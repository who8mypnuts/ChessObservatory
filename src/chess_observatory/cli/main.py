"""``chess-obs`` entry point.

Commands are thin: parse, load configuration, call one subsystem, render. All
real work lives in the package so the GUI, the CLI and plugins share it.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from chess_observatory import __version__
from chess_observatory.cli.doctor import render as render_doctor
from chess_observatory.config import (
    config_to_dict,
    load_config,
    parse_override,
    to_toml,
)
from chess_observatory.errors import ChessObservatoryError, CLIError
from chess_observatory.health import run_checks
from chess_observatory.logging import configure_logging, get_logger
from chess_observatory.paths import config_file
from chess_observatory.serialization import dumps


def build_parser() -> argparse.ArgumentParser:
    """The complete CLI surface for this phase."""
    parser = argparse.ArgumentParser(
        prog="chess-obs",
        description="A computational chess research workstation.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Use this configuration file instead of the default.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    doctor = subparsers.add_parser("doctor", help="diagnose the environment")
    doctor.add_argument("--json", action="store_true", help="print the report as JSON")

    ui = subparsers.add_parser("ui", help="open the workspace")
    ui.add_argument(
        "--smoke",
        action="store_true",
        help="open the window, process one event cycle, and exit (for CI).",
    )
    ui.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override one configuration value (repeatable).",
    )

    config = subparsers.add_parser("config", help="inspect configuration")
    config_sub = config.add_subparsers(dest="config_command", required=True, metavar="ACTION")

    show = config_sub.add_parser("show", help="print the effective configuration")
    show.add_argument("--json", action="store_true", help="print JSON including value sources")
    show.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override one configuration value (repeatable).",
    )
    config_sub.add_parser("path", help="print the configuration file path")

    subparsers.add_parser("version", help="print the version")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return _command_doctor(as_json=bool(args.json))
        if args.command == "ui":
            return _command_ui(
                path=_config_path(args),
                overrides=_parse_overrides(list(args.overrides)),
                smoke=bool(args.smoke),
            )
        if args.command == "config":
            return _command_config(args, path=_config_path(args))
        if args.command == "version":
            print(f"chess-obs {__version__}")
            return 0
        raise CLIError(f"Unknown command {args.command!r}.")
    except ChessObservatoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Canceled.", file=sys.stderr)
        return 130


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _command_doctor(*, as_json: bool) -> int:
    report = run_checks()
    if as_json:
        print(dumps(report.to_dict()))
    else:
        print(render_doctor(report))
    return report.exit_code


def _command_ui(*, path: Path | None, overrides: dict[str, str], smoke: bool) -> int:
    loaded = load_config(path, cli_overrides=overrides)
    setup = configure_logging(loaded.config.app.log_level)
    logger = get_logger("cli.ui")
    logger.info(
        "opening workspace version=%s theme=%s log=%s",
        __version__,
        loaded.config.ui.theme,
        setup.log_file,
    )
    try:
        from chess_observatory.ui.launch import run as run_ui
    except ImportError as exc:
        raise CLIError(
            "The graphical interface is unavailable.",
            hint="Run 'uv sync' to install PySide6, then try again.",
            context={"error": str(exc)},
        ) from exc

    if smoke:
        run_ui(loaded.config, smoke=True)
        print("UI smoke test: ok")
        return 0
    return run_ui(loaded.config)


def _command_config(args: argparse.Namespace, *, path: Path | None) -> int:
    action = args.config_command
    if action == "path":
        print(path if path is not None else config_file())
        return 0

    loaded = load_config(path, cli_overrides=_parse_overrides(list(args.overrides)))
    if bool(args.json):
        print(
            dumps(
                {
                    "path": loaded.path,
                    "config": config_to_dict(loaded.config),
                    "sources": dict(loaded.sources),
                }
            )
        )
        return 0

    overridden = [key for key, source in sorted(loaded.sources.items()) if source != "default"]
    print("# Chess Observatory configuration")
    print(f"# file: {loaded.path}{'' if loaded.path.exists() else ' (missing; defaults in use)'}")
    print(f"# overrides: {', '.join(overridden) if overridden else 'none (defaults)'}")
    print()
    print(to_toml(loaded.config), end="")
    return 0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _config_path(args: argparse.Namespace) -> Path | None:
    if args.config:
        return Path(args.config).expanduser()
    from_env = os.environ.get("CHESS_OBS_CONFIG")
    if from_env:
        return Path(from_env).expanduser()
    return None


def _parse_overrides(raw: list[str]) -> dict[str, str]:
    return dict(parse_override(item) for item in raw)


if __name__ == "__main__":
    raise SystemExit(main())
