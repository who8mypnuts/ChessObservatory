"""Layered configuration: precedence, migration, validation, round-trip."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from chess_observatory.config import (
    CURRENT_CONFIG_VERSION,
    FIELD_SPECS,
    Config,
    ConfigParseError,
    MlConfig,
    SearchConfig,
    UiConfig,
    env_name,
    load_config,
    parse_override,
    save_config,
    to_toml,
)
from chess_observatory.errors import ConfigMigrationError
from chess_observatory.serialization import dumps, from_dataclass


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_are_the_documented_ones(config_path: Path) -> None:
    loaded = load_config(config_path, env={})
    assert loaded.config == Config()
    assert loaded.config.ui.theme == "observatory-dark"
    assert loaded.config.ui.density == "comfortable"
    assert loaded.config.search.threads == 1
    assert loaded.config.ml.enabled is False
    assert loaded.path == config_path
    assert set(loaded.sources.values()) == {"default"}
    assert set(loaded.sources) == {spec.key for spec in FIELD_SPECS}


def test_user_file_overrides_defaults(config_path: Path) -> None:
    write(
        config_path,
        """
config_version = 1

[ui]
theme = "midnight"
motion = false

[search]
threads = 4
""",
    )
    loaded = load_config(config_path, env={})
    assert loaded.config.ui.theme == "midnight"
    assert loaded.config.ui.motion is False
    assert loaded.config.search.threads == 4
    assert loaded.config.ui.density == "comfortable"
    assert loaded.source_of("ui.theme") == "user"
    assert loaded.source_of("ui.density") == "default"


def test_precedence_cli_beats_env_beats_user_beats_default(config_path: Path) -> None:
    write(config_path, '[ui]\ntheme = "midnight"\n')
    loaded = load_config(
        config_path,
        env={"CHESS_OBS_UI_THEME": "carbon", "CHESS_OBS_UI_DENSITY": "compact"},
        cli_overrides={"ui.theme": "nord"},
    )
    assert loaded.config.ui.theme == "nord"
    assert loaded.config.ui.density == "compact"
    assert loaded.source_of("ui.theme") == "cli"
    assert loaded.source_of("ui.density") == "env"
    assert loaded.source_of("ui.board_palette") == "default"


def test_environment_name_is_derived_from_the_key() -> None:
    assert env_name("ui.theme") == "CHESS_OBS_UI_THEME"
    assert env_name("ml.enabled") == "CHESS_OBS_ML_ENABLED"


def test_environment_values_are_coerced(config_path: Path) -> None:
    loaded = load_config(
        config_path,
        env={
            "CHESS_OBS_ML_ENABLED": "yes",
            "CHESS_OBS_SEARCH_THREADS": "8",
            "CHESS_OBS_APP_LOG_LEVEL": "debug",
        },
    )
    assert loaded.config.ml.enabled is True
    assert loaded.config.search.threads == 8
    assert loaded.config.app.log_level == "DEBUG"


def test_version_zero_layout_is_migrated(config_path: Path) -> None:
    write(
        config_path,
        """
theme = "parchment"
ml_enabled = true

[engine]
threads = 6
hash_mb = 512
""",
    )
    loaded = load_config(config_path, env={})
    assert loaded.config.ui.theme == "parchment"
    assert loaded.config.ml.enabled is True
    assert loaded.config.search.threads == 6
    assert loaded.config.search.hash_mb == 512
    assert loaded.config.config_version == CURRENT_CONFIG_VERSION


def test_config_from_the_future_is_refused(config_path: Path) -> None:
    write(config_path, "config_version = 99\n")
    with pytest.raises(ConfigMigrationError) as caught:
        load_config(config_path, env={})
    assert "newer" in str(caught.value).lower()


def test_unknown_key_is_an_error_with_a_hint(config_path: Path) -> None:
    write(config_path, "[ui]\ncolour = 'red'\n")
    with pytest.raises(ConfigParseError) as caught:
        load_config(config_path, env={})
    assert "colour" in str(caught.value)
    assert "Known keys" in str(caught.value)


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ("[ui]\nmotion = 'maybe'\n", "boolean"),
        ("[ui]\ndensity = 'huge'\n", "compact"),
        ("[search]\nthreads = 'many'\n", "integer"),
        ("[search]\nthreads = 0\n", "at least 1"),
        ("[ui]\ntheme = ['a', 'b']\n", "not a list"),
        ("[ml]\ndevice = 'quantum'\n", "cpu"),
    ],
)
def test_invalid_values_name_the_key(config_path: Path, body: str, fragment: str) -> None:
    write(config_path, body)
    with pytest.raises(ConfigParseError) as caught:
        load_config(config_path, env={})
    assert fragment in str(caught.value)


def test_invalid_toml_is_reported_with_the_path(config_path: Path) -> None:
    write(config_path, "[ui\ntheme = 'x'\n")
    with pytest.raises(ConfigParseError) as caught:
        load_config(config_path, env={})
    assert str(config_path) in str(caught.value)


def test_parse_override() -> None:
    assert parse_override("ui.theme = midnight") == ("ui.theme", "midnight")
    with pytest.raises(ConfigParseError):
        parse_override("ui.theme")
    with pytest.raises(ConfigParseError) as caught:
        parse_override("ui.nope=1")
    assert "ui.nope" in str(caught.value)


def test_save_and_load_round_trip(config_path: Path) -> None:
    original = Config(
        ui=UiConfig(theme="everforest", board_palette="walnut", density="compact", motion=False),
        ml=MlConfig(enabled=True, device="auto", model="eval.nnue.small"),
    )
    saved = save_config(original, config_path)
    assert saved == config_path
    assert config_path.is_file()

    loaded = load_config(config_path, env={})
    assert loaded.config == original


def test_toml_output_is_parseable_and_omits_none(config_path: Path) -> None:
    text = to_toml(Config())
    data = tomllib.loads(text)
    assert data["config_version"] == CURRENT_CONFIG_VERSION
    assert data["ui"]["theme"] == "observatory-dark"
    assert "model" not in data["ml"]
    assert "#" not in text


def test_config_survives_json_round_trip() -> None:
    original = Config(
        ui=UiConfig(theme="nord"),
        search=SearchConfig(threads=3, hash_mb=64, default_profile="deep"),
    )
    restored = from_dataclass(Config, json.loads(dumps(original)))
    assert restored == original
