"""XDG base-directory helpers.

One place decides where configuration, data, cache and logs live, so the CLI,
the UI, tests and packaging never disagree (plan §13.5).

All functions read the environment each call: tests monkeypatch ``XDG_*`` and
expect the change to take effect without reloading modules.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "chess-observatory"


def _base(env_var: str, fallback: str) -> Path:
    value = os.environ.get(env_var)
    if value:
        return Path(value).expanduser()
    return Path.home() / fallback


def config_dir() -> Path:
    """Directory for configuration files (``$XDG_CONFIG_HOME``)."""
    return _base("XDG_CONFIG_HOME", ".config") / APP_DIR_NAME


def config_file() -> Path:
    """The single TOML configuration file."""
    return config_dir() / "config.toml"


def data_dir() -> Path:
    """Directory for the store, corpora and user assets (``$XDG_DATA_HOME``)."""
    return _base("XDG_DATA_HOME", ".local/share") / APP_DIR_NAME


def cache_dir() -> Path:
    """Disposable cache (``$XDG_CACHE_HOME``)."""
    return _base("XDG_CACHE_HOME", ".cache") / APP_DIR_NAME


def state_dir() -> Path:
    """Persistent state that is not user data, such as logs (``$XDG_STATE_HOME``)."""
    return _base("XDG_STATE_HOME", ".local/state") / APP_DIR_NAME


def log_dir() -> Path:
    """Directory for rotating log files."""
    return state_dir() / "logs"
