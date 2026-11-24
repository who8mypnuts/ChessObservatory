"""Environment diagnosis behind ``chess-obs doctor`` (plan Phase 0, step 11).

Checks are independent and guarded: one broken check reports itself as a
failure instead of crashing the report. The report is structured so the CLI,
tests and bug reports all consume the same facts.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from typing import Any

from chess_observatory import __version__, paths

MINIMUM_PYTHON = (3, 14)
REFERENCE_ENGINES = ("stockfish", "berserk", "ethereal", "rubichess", "igel", "lc0")


class CheckStatus(StrEnum):
    """Severity of one diagnostic result."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class Check:
    """One named diagnosis."""

    id: str
    title: str
    status: CheckStatus
    detail: str
    fix: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    """The full diagnosis."""

    checks: tuple[Check, ...]
    generated_at: datetime

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if check.status is CheckStatus.FAIL)

    @property
    def warnings(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if check.status is CheckStatus.WARN)

    @property
    def status(self) -> CheckStatus:
        if self.failures:
            return CheckStatus.FAIL
        if self.warnings:
            return CheckStatus.WARN
        return CheckStatus.OK

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "exit_code": self.exit_code,
            "generated_at": self.generated_at.isoformat(),
            "version": __version__,
            "checks": [
                {
                    "id": check.id,
                    "title": check.title,
                    "status": check.status.value,
                    "detail": check.detail,
                    "fix": check.fix,
                }
                for check in self.checks
            ],
        }


def run_checks() -> HealthReport:
    """Run every diagnostic and return the report."""
    checks = (
        _guard("platform", "Operating system", _check_platform),
        _guard("python", "Python version", _check_python),
        _guard("package", "Chess Observatory package", _check_package),
        _guard("pyside6", "PySide6 (Qt)", _check_pyside6),
        _guard("numpy", "numpy", _check_numpy),
        _guard("pyarrow", "pyarrow", _check_pyarrow),
        _guard("display", "Display server", _check_display),
        _guard("config-dir", "Configuration directory", _check_config_dir),
        _guard("data-dir", "Data directory", _check_data_dir),
        _guard("log-dir", "Log directory", _check_log_dir),
        _guard("engines", "Reference engines", _check_engines),
        _guard("assets", "Asset ledger", _check_assets),
        _guard("store", "Store", _check_store),
    )
    return HealthReport(checks=checks, generated_at=datetime.now(UTC))


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def _check_platform() -> Check:
    system = platform.system()
    if system == "Linux":
        return Check(
            "platform", "Operating system", CheckStatus.OK, f"Linux ({platform.release()})"
        )
    return Check(
        "platform",
        "Operating system",
        CheckStatus.FAIL,
        f"{system} is not supported.",
        "Chess Observatory targets Linux only (plan D9).",
    )


def _check_python() -> Check:
    current = sys.version_info[:2]
    detail = f"{sys.version.split()[0]} at {sys.executable}"
    if current >= MINIMUM_PYTHON:
        return Check("python", "Python version", CheckStatus.OK, detail)
    required = ".".join(str(part) for part in MINIMUM_PYTHON)
    return Check(
        "python",
        "Python version",
        CheckStatus.FAIL,
        f"{detail} (need {required}+)",
        f"Install Python {required}+, for example: uv python install {required}",
    )


def _check_package() -> Check:
    try:
        installed = metadata.version("chess-observatory")
    except metadata.PackageNotFoundError:
        return Check(
            "package",
            "Chess Observatory package",
            CheckStatus.WARN,
            f"not installed in this environment (source version {__version__})",
            "Run: uv sync",
        )
    return Check(
        "package",
        "Chess Observatory package",
        CheckStatus.OK,
        f"{installed}",
    )


def _module_check(
    check_id: str,
    title: str,
    module: str,
    distribution: str | None = None,
) -> Check:
    if importlib.util.find_spec(module) is None:
        return Check(
            check_id,
            title,
            CheckStatus.FAIL,
            f"{module} is not installed",
            "Run: uv sync",
        )
    version = "unknown version"
    if distribution is not None:
        try:
            version = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            version = "unknown version"
    return Check(check_id, title, CheckStatus.OK, f"{module} {version}")


def _check_pyside6() -> Check:
    return _module_check("pyside6", "PySide6 (Qt)", "PySide6", "PySide6")


def _check_numpy() -> Check:
    return _module_check("numpy", "numpy", "numpy", "numpy")


def _check_pyarrow() -> Check:
    return _module_check("pyarrow", "pyarrow", "pyarrow", "pyarrow")


def _check_display() -> Check:
    session = os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")
    if session:
        kind = "Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
        return Check("display", "Display server", CheckStatus.OK, f"{kind} ({session})")
    return Check(
        "display",
        "Display server",
        CheckStatus.WARN,
        "no DISPLAY or WAYLAND_DISPLAY (headless session)",
        "CLI commands work headless; the GUI needs a graphical session.",
    )


def _check_writable(check_id: str, title: str, directory: Path) -> Check:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=directory,
            prefix=".chessobs-write-test-",
            delete=True,
        ):
            pass
    except OSError as exc:
        return Check(
            check_id,
            title,
            CheckStatus.FAIL,
            f"{directory} is not writable ({exc.strerror or exc})",
            "Fix the directory permissions or point the XDG variable elsewhere.",
        )
    return Check(check_id, title, CheckStatus.OK, str(directory))


def _check_config_dir() -> Check:
    return _check_writable("config-dir", "Configuration directory", paths.config_dir())


def _check_data_dir() -> Check:
    return _check_writable("data-dir", "Data directory", paths.data_dir())


def _check_log_dir() -> Check:
    return _check_writable("log-dir", "Log directory", paths.log_dir())


def _check_engines() -> Check:
    found = [name for name in REFERENCE_ENGINES if shutil.which(name) is not None]
    if found:
        return Check("engines", "Reference engines", CheckStatus.OK, ", ".join(found))
    return Check(
        "engines",
        "Reference engines",
        CheckStatus.WARN,
        "none found on PATH",
        "Optional: install Stockfish or another UCI engine for reference analysis.",
    )


def _repo_root() -> Path | None:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "assets").is_dir():
            return candidate
    return None


def _check_assets() -> Check:
    root = _repo_root()
    if root is None:
        return Check(
            "assets",
            "Asset ledger",
            CheckStatus.WARN,
            "not running from a source checkout",
            "Run this check from the repository root to verify licensing coverage.",
        )
    ledger = root / "assets" / "LICENSES.md"
    if not ledger.is_file():
        return Check(
            "assets",
            "Asset ledger",
            CheckStatus.FAIL,
            f"{ledger} is missing",
            "Every bundled asset needs a ledger entry (plan §13.1).",
        )
    return Check("assets", "Asset ledger", CheckStatus.OK, str(ledger.relative_to(root)))


def _check_store() -> Check:
    # The store arrives in Phase 14. Until then, prove the parent is writable.
    directory = paths.data_dir() / "store"
    return _check_writable("store", "Store", directory)


# --------------------------------------------------------------------------- #
# Guard
# --------------------------------------------------------------------------- #
def _guard(check_id: str, title: str, check: Callable[[], Check]) -> Check:
    try:
        return check()
    except Exception as exc:  # a diagnostic must never crash itself
        return Check(
            check_id,
            title,
            CheckStatus.FAIL,
            f"check crashed: {type(exc).__name__}: {exc}",
            "Report this with the full doctor output.",
        )
