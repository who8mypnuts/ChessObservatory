"""Search limits, deadlines and the soft/hard time-management split (Phase 2, step 2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from chess_observatory.core.pieces import Color


class Effort(StrEnum):
    """Coarse effort tiers that map onto limits (preset names are later)."""

    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"
    PROOF = "proof"


@dataclass(frozen=True, slots=True)
class Deadline:
    """Absolute soft and hard stop times, in monotonic milliseconds."""

    soft: float
    hard: float


@dataclass(frozen=True, slots=True)
class SearchLimits:
    """Everything a bounded search needs, including the time-control split."""

    movetime_ms: float = 0.0
    wtime_ms: float = 0.0
    btime_ms: float = 0.0
    winc_ms: float = 0.0
    binc_ms: float = 0.0
    depth: int = 0
    nodes: int = 0
    mate: int = 0
    infinite: bool = False
    multi_pv: int = 1
    soft_hard_ratio: float = 0.75
    move_overhead_ms: float = 0.0
    max_depth: int = 0

    def budget_ms(self, color: Color, *, elapsed_ms: float = 0.0) -> float:
        """Time the side ``color`` may spend, in milliseconds."""
        if self.infinite:
            return float("inf")
        if self.movetime_ms > 0.0:
            return self.movetime_ms
        if color is Color.WHITE:
            return max(0.0, self.wtime_ms - elapsed_ms + self.winc_ms)
        return max(0.0, self.btime_ms - elapsed_ms + self.binc_ms)

    def deadline(
        self, *, now: float = 0.0, elapsed_ms: float = 0.0, color: Color
    ) -> Deadline | None:
        """Soft/hard deadline; ``None`` when the limits do not impose a time ceiling.

        Depth-only limits without a time control produce no deadline. The soft
        stop time is ``soft_hard_ratio * budget`` after ``now``; the hard stop is
        the full budget after ``now``, plus the move overhead compensation for
        transport latency. The soft stop never exceeds the hard stop.
        """
        has_time_control = self.movetime_ms > 0.0 or self.wtime_ms > 0.0 or self.btime_ms > 0.0
        if self.infinite or not has_time_control:
            return None
        budget = self.budget_ms(color, elapsed_ms=elapsed_ms)
        soft = now + budget * self.soft_hard_ratio
        hard = now + budget + self.move_overhead_ms
        if soft > hard:
            soft = hard
        return Deadline(soft=soft, hard=hard)
