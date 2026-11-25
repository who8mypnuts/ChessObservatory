"""Search limits, deadlines and the soft/hard time-management split."""

from __future__ import annotations

from chess_observatory.core.pieces import Color
from chess_observatory.search.limits import Effort, SearchLimits


def test_infinite_limits_have_no_deadline() -> None:
    limits = SearchLimits(infinite=True)
    assert limits.deadline(now=1000.0, elapsed_ms=500.0, color=Color.WHITE) is None
    assert limits.budget_ms(Color.BLACK, elapsed_ms=500.0) == float("inf")


def test_depth_only_limits_have_no_deadline() -> None:
    limits = SearchLimits(depth=5, nodes=1000)
    assert limits.deadline(now=1000.0, elapsed_ms=0.0, color=Color.WHITE) is None


def test_depth_only_with_time_control_has_a_deadline() -> None:
    limits = SearchLimits(depth=5, movetime_ms=1000.0)
    deadline = limits.deadline(now=1000.0, elapsed_ms=0.0, color=Color.WHITE)
    assert deadline is not None
    assert deadline.soft == 1000.0 + 1000.0 * 0.75
    assert deadline.hard == 1000.0 + 1000.0
    assert deadline.soft <= deadline.hard


def test_soft_hard_ratio_splits_the_budget() -> None:
    limits = SearchLimits(movetime_ms=1000.0, soft_hard_ratio=0.5)
    deadline = limits.deadline(now=500.0, elapsed_ms=0.0, color=Color.BLACK)
    assert deadline is not None
    assert deadline.soft == 500.0 + 500.0
    assert deadline.hard == 500.0 + 1000.0


def test_move_overhead_extends_the_hard_deadline() -> None:
    limits = SearchLimits(movetime_ms=1000.0, move_overhead_ms=25.0)
    deadline = limits.deadline(now=0.0, elapsed_ms=0.0, color=Color.WHITE)
    assert deadline is not None
    assert deadline.hard == 1025.0


def test_clock_budget_accounts_for_increments_and_elapsed_time() -> None:
    limits = SearchLimits(wtime_ms=60000.0, winc_ms=2000.0)
    assert limits.budget_ms(Color.WHITE, elapsed_ms=30000.0) == 32000.0
    assert limits.budget_ms(Color.BLACK, elapsed_ms=0.0) == 0.0


def test_budget_is_zero_for_an_exhausted_clock() -> None:
    limits = SearchLimits(wtime_ms=5000.0, btime_ms=4000.0)
    assert limits.budget_ms(Color.WHITE, elapsed_ms=6000.0) == 0.0
    assert limits.budget_ms(Color.BLACK, elapsed_ms=4000.0) == 0.0


def test_soft_deadline_never_exceeds_the_hard_deadline() -> None:
    limits = SearchLimits(movetime_ms=1000.0, soft_hard_ratio=1.0)
    deadline = limits.deadline(now=0.0, elapsed_ms=0.0, color=Color.WHITE)
    assert deadline is not None
    assert deadline.soft == deadline.hard


def test_effort_is_a_closed_set() -> None:
    assert [effort.value for effort in Effort] == ["fast", "balanced", "deep", "proof"]
    assert issubclass(Effort, str) and issubclass(Effort, object)
