"""CLI surface: exit codes, output shape, configuration overrides."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from chess_observatory import __version__
from chess_observatory.cli.main import _parse_overrides, main
from chess_observatory.config import Config, load_config


@pytest.fixture(autouse=True)
def isolated_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("CHESS_OBS_CONFIG", raising=False)


@pytest.fixture
def missing_config(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"chess-obs {__version__}"


def test_version_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0


def test_doctor_human_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "environment report" in out
    assert "checks:" in out
    assert "\u2713 Python version" in out


def test_doctor_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] in {"ok", "warn"}
    assert payload["version"] == __version__
    assert any(check["id"] == "python" for check in payload["checks"])


def test_config_show_prints_toml(capsys: pytest.CaptureFixture[str], missing_config: Path) -> None:
    assert main(["--config", str(missing_config), "config", "show"]) == 0
    out = capsys.readouterr().out
    assert "# Chess Observatory configuration" in out
    data = tomllib.loads("\n".join(line for line in out.splitlines() if not line.startswith("#")))
    assert data["ui"]["theme"] == "observatory-dark"


def test_config_show_reports_value_sources(
    capsys: pytest.CaptureFixture[str], missing_config: Path
) -> None:
    args = [
        "--config",
        str(missing_config),
        "config",
        "show",
        "--json",
        "--set",
        "ui.theme=carbon",
    ]
    assert main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config"]["ui"]["theme"] == "carbon"
    assert payload["sources"]["ui.theme"] == "cli"
    assert payload["sources"]["ui.density"] == "default"


def test_last_override_wins(missing_config: Path) -> None:
    overrides = _parse_overrides(["ui.theme=a", "ui.theme=b"])
    loaded = load_config(missing_config, env={}, cli_overrides=overrides)
    assert loaded.config.ui.theme == "b"


def test_config_show_reads_a_user_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[ui]\ntheme = "midnight"\n', encoding="utf-8")
    assert main(["--config", str(path), "config", "show"]) == 0
    out = capsys.readouterr().out
    assert 'theme = "midnight"' in out


def test_config_path_command(capsys: pytest.CaptureFixture[str], missing_config: Path) -> None:
    assert main(["--config", str(missing_config), "config", "path"]) == 0
    assert capsys.readouterr().out.strip() == str(missing_config)


def test_unknown_override_is_a_clean_error(
    capsys: pytest.CaptureFixture[str], missing_config: Path
) -> None:
    assert main(["--config", str(missing_config), "config", "show", "--set", "ui.nope=1"]) == 2
    err = capsys.readouterr().err
    assert "ui.nope" in err
    assert "Hint:" in err


def test_missing_command_exits_with_argparse_error() -> None:
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


@pytest.mark.ui
def test_ui_smoke_exits_cleanly(capsys: pytest.CaptureFixture[str], missing_config: Path) -> None:
    args = ["--config", str(missing_config), "ui", "--smoke", "--set", "ui.theme=midnight"]
    assert main(args) == 0
    assert "UI smoke test: ok" in capsys.readouterr().out


def test_config_defaults_are_reachable_programmatically() -> None:
    assert Config().ml.enabled is False
