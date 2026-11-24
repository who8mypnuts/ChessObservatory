"""XDG path helpers respond to the environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from chess_observatory import paths

XDG_VARS = (
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
)


@pytest.fixture
def isolated_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for name in XDG_VARS:
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


def test_each_directory_uses_its_xdg_variable(isolated_xdg: Path) -> None:
    assert paths.config_dir() == isolated_xdg / "xdg_config_home" / paths.APP_DIR_NAME
    assert paths.data_dir() == isolated_xdg / "xdg_data_home" / paths.APP_DIR_NAME
    assert paths.cache_dir() == isolated_xdg / "xdg_cache_home" / paths.APP_DIR_NAME
    assert paths.log_dir() == (isolated_xdg / "xdg_state_home" / paths.APP_DIR_NAME / "logs")


def test_config_file_is_inside_config_dir(isolated_xdg: Path) -> None:
    assert paths.config_file().parent == paths.config_dir()
    assert paths.config_file().name == "config.toml"


def test_unset_variables_fall_back_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in XDG_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths.config_dir() == tmp_path / ".config" / paths.APP_DIR_NAME
    assert paths.data_dir() == tmp_path / ".local/share" / paths.APP_DIR_NAME
    assert paths.cache_dir() == tmp_path / ".cache" / paths.APP_DIR_NAME
    assert paths.log_dir() == tmp_path / ".local/state" / paths.APP_DIR_NAME / "logs"
