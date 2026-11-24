"""Typed, layered configuration (plan §13.5).

Precedence, lowest to highest: built-in defaults, user TOML file, environment,
CLI overrides. Unknown keys are errors, not silently ignored, and every
effective value can report which layer supplied it.

The file is TOML, versioned, and migrated forward. Migration is explicit and
tested; a file from a newer version is refused rather than half-understood.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Literal

from chess_observatory.errors import (
    ConfigError,
    ConfigMigrationError,
    ConfigParseError,
    ConfigWriteError,
)
from chess_observatory.paths import config_file

CURRENT_CONFIG_VERSION = 1
ENV_PREFIX = "CHESS_OBS_"

FieldKind = Literal["str", "int", "bool"]
Source = Literal["default", "user", "env", "cli"]


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AppConfig:
    """Process-wide behaviour."""

    log_level: str = "INFO"


@dataclass(frozen=True, slots=True)
class UiConfig:
    """Appearance. Theme ids are validated by the theme registry (Phase 6)."""

    theme: str = "observatory-dark"
    board_palette: str = "classic-green"
    density: str = "comfortable"
    motion: bool = True


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Defaults for the own engine. Parameter details arrive in Phase 2."""

    default_profile: str = "standard"
    threads: int = 1
    hash_mb: int = 256


@dataclass(frozen=True, slots=True)
class MlConfig:
    """Machine learning is off until a user enables it (plan D7, §2.1)."""

    enabled: bool = False
    device: str = "cpu"
    model: str | None = None


@dataclass(frozen=True, slots=True)
class Config:
    """The whole configuration tree."""

    config_version: int = CURRENT_CONFIG_VERSION
    app: AppConfig = field(default_factory=AppConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    ml: MlConfig = field(default_factory=MlConfig)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Metadata for one leaf value: used for env names, coercion and docs."""

    key: str
    kind: FieldKind
    description: str
    minimum: int | None = None
    choices: tuple[str, ...] = ()


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "app.log_level",
        "str",
        "Log verbosity: DEBUG, INFO, WARNING, ERROR or CRITICAL.",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    ),
    FieldSpec("ui.theme", "str", "Theme pack id (20 ship with the app)."),
    FieldSpec("ui.board_palette", "str", "Board palette id, independent of the theme."),
    FieldSpec(
        "ui.density",
        "str",
        "Row height: comfortable or compact.",
        choices=("comfortable", "compact"),
    ),
    FieldSpec("ui.motion", "bool", "Enable explanatory animation."),
    FieldSpec("search.default_profile", "str", "Default effort profile."),
    FieldSpec("search.threads", "int", "Search threads (1 is reproducible).", minimum=1),
    FieldSpec("search.hash_mb", "int", "Transposition-table size in MiB.", minimum=1),
    FieldSpec("ml.enabled", "bool", "Enable learned components (off by default)."),
    FieldSpec(
        "ml.device",
        "str",
        "Inference device: cpu, cuda, rocm or auto.",
        choices=("cpu", "cuda", "rocm", "auto"),
    ),
    FieldSpec("ml.model", "str", "Preferred model id; empty means none."),
)

SPEC_BY_KEY: Mapping[str, FieldSpec] = {spec.key: spec for spec in FIELD_SPECS}


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    """Effective configuration plus where each value came from."""

    config: Config
    sources: Mapping[str, Source]
    path: Path

    def source_of(self, key: str) -> Source:
        return self.sources.get(key, "default")


# --------------------------------------------------------------------------- #
# Reading and migration
# --------------------------------------------------------------------------- #
def env_name(key: str) -> str:
    """Environment variable for a config key: ``ui.theme`` → ``CHESS_OBS_UI_THEME``."""
    return ENV_PREFIX + key.upper().replace(".", "_")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Cannot read configuration file {path}: {exc.strerror or exc}.",
            hint="Check the path and its permissions, or remove the file to use defaults.",
            context={"path": str(path)},
        ) from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigParseError(
            f"Invalid TOML in {path}: {exc}",
            hint="Configuration is TOML; check quoting and section headers.",
            context={"path": str(path)},
        ) from exc
    return data


def migrate_config(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate a raw config mapping to :data:`CURRENT_CONFIG_VERSION`.

    Version 0 is the pre-release flat layout: appearance keys at top level and
    engine knobs under ``[engine]``. It is folded into the current sections once,
    so early testers' files keep working.
    """
    data: dict[str, Any] = dict(raw)
    version_raw = data.get("config_version", 0)
    if isinstance(version_raw, bool) or not isinstance(version_raw, int):
        raise ConfigMigrationError(
            "config_version must be an integer.",
            context={"config_version": repr(version_raw)},
        )
    version = version_raw
    if version > CURRENT_CONFIG_VERSION:
        raise ConfigMigrationError(
            f"Configuration version {version} is newer than supported version "
            f"{CURRENT_CONFIG_VERSION}.",
            hint="Upgrade Chess Observatory, or move the file aside to start fresh.",
            context={"path_version": version, "supported": CURRENT_CONFIG_VERSION},
        )
    if version == 0:
        data = _migrate_0_to_1(data)
    data["config_version"] = CURRENT_CONFIG_VERSION
    return data


def _migrate_0_to_1(data: dict[str, Any]) -> dict[str, Any]:
    ui = dict(data.get("ui") or {})
    for key in ("theme", "board_palette", "density", "motion"):
        if key in data:
            ui.setdefault(key, data.pop(key))
    if ui:
        data["ui"] = ui

    engine = dict(data.get("engine") or {})
    search = dict(data.get("search") or {})
    for key in ("threads", "hash_mb"):
        if key in engine:
            search.setdefault(key, engine.pop(key))
    if search:
        data["search"] = search
    data.pop("engine", None)

    if "ml_enabled" in data:
        ml = dict(data.get("ml") or {})
        ml.setdefault("enabled", data.pop("ml_enabled"))
        data["ml"] = ml
    return data


def flatten_config(
    data: Mapping[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[str, Any]]:
    """Yield ``(dotted_key, scalar)`` for every leaf, rejecting nested arrays."""
    for key, value in data.items():
        path = (*prefix, key)
        if isinstance(value, Mapping):
            yield from flatten_config(value, path)
        elif isinstance(value, list | tuple):
            raise ConfigParseError(
                f"Configuration key '{'.'.join(path)}' must be a single value, not a list.",
                hint="Configuration values are strings, integers or booleans.",
            )
        else:
            yield ".".join(path), value


# --------------------------------------------------------------------------- #
# Coercion and validation
# --------------------------------------------------------------------------- #
def _coerce(spec: FieldSpec, raw: Any) -> str | int | bool:
    if spec.kind == "bool":
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        raise ConfigParseError(
            f"'{spec.key}' expects a boolean, got {raw!r}.",
            hint="Use true or false.",
            context={"key": spec.key},
        )

    if spec.kind == "int":
        if isinstance(raw, bool):
            raise ConfigParseError(f"'{spec.key}' expects an integer, got a boolean.")
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ConfigParseError(
                f"'{spec.key}' expects an integer, got {raw!r}.",
                context={"key": spec.key},
            ) from exc
        if spec.minimum is not None and value < spec.minimum:
            raise ConfigParseError(
                f"'{spec.key}' must be at least {spec.minimum}, got {value}.",
                context={"key": spec.key},
            )
        return value

    if raw is None:
        raise ConfigParseError(f"'{spec.key}' expects a string, got null.")
    text = str(raw)
    if spec.key == "app.log_level":
        text = text.upper()
    if spec.choices and text not in spec.choices:
        allowed = ", ".join(spec.choices)
        raise ConfigParseError(
            f"'{spec.key}' must be one of: {allowed} (got {text!r}).",
            context={"key": spec.key},
        )
    return text


def parse_override(text: str) -> tuple[str, str]:
    """Parse ``key=value`` from the CLI."""
    key, sep, value = text.partition("=")
    key = key.strip()
    if not sep or not key:
        raise ConfigParseError(
            f"Override {text!r} is not in key=value form.",
            hint="Example: --set ui.theme=midnight",
        )
    if key not in SPEC_BY_KEY:
        raise ConfigParseError(
            f"Unknown configuration key '{key}'.",
            hint=f"Known keys: {', '.join(sorted(SPEC_BY_KEY))}",
            context={"key": key},
        )
    return key, value.strip()


# --------------------------------------------------------------------------- #
# Layering
# --------------------------------------------------------------------------- #
def load_config(
    path: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cli_overrides: Mapping[str, str] | None = None,
) -> LoadedConfig:
    """Build the effective configuration from all four layers."""
    config_path = Path(path) if path is not None else config_file()
    environment = os.environ if env is None else env
    config = Config()
    sources: dict[str, Source] = {spec.key: "default" for spec in FIELD_SPECS}

    if config_path.exists():
        raw = migrate_config(_read_toml(config_path))
        for key, value in flatten_config(raw):
            if key == "config_version":
                continue
            spec = SPEC_BY_KEY.get(key)
            if spec is None:
                raise ConfigParseError(
                    f"Unknown configuration key '{key}' in {config_path}.",
                    hint=f"Known keys: {', '.join(sorted(SPEC_BY_KEY))}",
                    context={"path": str(config_path), "key": key},
                )
            config = _set_value(config, key, _coerce(spec, value))
            sources[key] = "user"

    for spec in FIELD_SPECS:
        name = env_name(spec.key)
        if name in environment:
            config = _set_value(config, spec.key, _coerce(spec, environment[name]))
            sources[spec.key] = "env"

    for key, raw_value in (cli_overrides or {}).items():
        spec = SPEC_BY_KEY.get(key)
        if spec is None:
            raise ConfigParseError(
                f"Unknown configuration key '{key}'.",
                hint=f"Known keys: {', '.join(sorted(SPEC_BY_KEY))}",
                context={"key": key},
            )
        config = _set_value(config, key, _coerce(spec, raw_value))
        sources[key] = "cli"

    return LoadedConfig(config=config, sources=sources, path=config_path)


def _set_value(config: Config, key: str, value: str | int | bool) -> Config:
    parts = key.split(".")

    def assign(node: Any, remaining: Sequence[str]) -> Any:
        head, *rest = remaining
        if not rest:
            return replace(node, **{head: value})
        return replace(node, **{head: assign(getattr(node, head), rest)})

    result: Config = assign(config, parts)
    return result


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
def to_toml(config: Config) -> str:
    """Serialise the configuration tree to TOML (stable key order)."""
    lines: list[str] = [f"config_version = {config.config_version}", ""]
    for top in fields(config):
        if top.name == "config_version":
            continue
        section = getattr(config, top.name)
        lines.append(f"[{top.name}]")
        for leaf in fields(section):
            value = getattr(section, leaf.name)
            if value is None:
                continue
            lines.append(f"{leaf.name} = {_toml_scalar(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise ConfigWriteError(f"Cannot serialise config value {value!r}.")


def save_config(config: Config, path: Path | None = None) -> Path:
    """Write the configuration atomically and return the path."""
    target = Path(path) if path is not None else config_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(to_toml(config), encoding="utf-8")
        temporary.replace(target)
    except OSError as exc:
        raise ConfigWriteError(
            f"Cannot write configuration to {target}: {exc.strerror or exc}.",
            hint="Check that the directory is writable.",
            context={"path": str(target)},
        ) from exc
    return target


def config_to_dict(config: Config) -> dict[str, Any]:
    """Plain-dict view used by ``--json`` output and reports."""
    return dataclasses.asdict(config)
