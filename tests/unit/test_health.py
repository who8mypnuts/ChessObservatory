"""Doctor checks are structured, guarded and JSON-safe."""

from __future__ import annotations

from pathlib import Path

import pytest

from chess_observatory import health
from chess_observatory.health import Check, CheckStatus, HealthReport, run_checks
from chess_observatory.serialization import dumps


@pytest.fixture(autouse=True)
def isolated_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


def test_run_checks_covers_the_environment() -> None:
    report = run_checks()
    ids = [check.id for check in report.checks]
    assert len(ids) == len(set(ids))
    assert {"platform", "python", "pyside6", "numpy", "display", "config-dir"} <= set(ids)
    assert all(check.title and check.detail for check in report.checks)


def test_report_is_json_serialisable() -> None:
    report = run_checks()
    payload = dumps(report.to_dict())
    assert '"checks"' in payload
    assert '"generated_at"' in payload
    assert '"status"' in payload


def test_failures_drive_the_exit_code() -> None:
    ok = Check("a", "A", CheckStatus.OK, "fine")
    warn = Check("b", "B", CheckStatus.WARN, "meh", "do something")
    fail = Check("c", "C", CheckStatus.FAIL, "broken", "fix it")
    assert HealthReport((ok,), health.datetime.now(health.UTC)).exit_code == 0
    warn_report = HealthReport((ok, warn), health.datetime.now(health.UTC))
    assert warn_report.exit_code == 0
    assert warn_report.status is CheckStatus.WARN
    assert HealthReport((warn, fail), health.datetime.now(health.UTC)).exit_code == 1


def test_a_crashing_check_becomes_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> Check:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(health, "_check_numpy", boom)
    report = run_checks()
    numpy_check = next(check for check in report.checks if check.id == "numpy")
    assert numpy_check.status is CheckStatus.FAIL
    assert "kaboom" in numpy_check.detail


def test_missing_display_is_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    check = health._check_display()
    assert check.status is CheckStatus.WARN
    assert check.fix is not None


def test_unwritable_directory_is_a_failure(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    check = health._check_writable("x", "X", blocker / "sub")
    assert check.status is CheckStatus.FAIL
    assert "not writable" in check.detail
