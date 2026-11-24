"""Human and JSON rendering for ``chess-obs doctor``."""

from __future__ import annotations

from chess_observatory import __version__
from chess_observatory.health import CheckStatus, HealthReport

_SYMBOL = {
    CheckStatus.OK: "\u2713",  # check mark
    CheckStatus.WARN: "!",
    CheckStatus.FAIL: "\u2717",  # ballot x
}


def render(report: HealthReport) -> str:
    """Render the report for a terminal."""
    lines = [
        f"Chess Observatory {__version__} \u2014 environment report",
        "",
    ]
    width = max((len(check.title) for check in report.checks), default=0)
    for check in report.checks:
        lines.append(f"  {_SYMBOL[check.status]} {check.title:<{width}}  {check.detail}")
        if check.status is not CheckStatus.OK and check.fix:
            lines.append(f"    {' ' * (width + 2)}\u2192 {check.fix}")

    lines.append("")
    summary = (
        f"{len(report.checks)} checks: "
        f"{len(report.checks) - len(report.warnings) - len(report.failures)} ok, "
        f"{len(report.warnings)} warning(s), "
        f"{len(report.failures)} problem(s)"
    )
    lines.append(summary)
    if report.failures:
        lines.append("Fix the items marked \u2717 and run 'chess-obs doctor' again.")
    else:
        lines.append("Environment ready. Start the workspace with: uv run chess-obs ui")
    return "\n".join(lines)
