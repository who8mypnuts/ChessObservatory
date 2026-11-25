"""Bounded search trace: per-depth summaries and the final result (Phase 2, step 8)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DepthRecord:
    """One completed deepening pass."""

    depth: int
    score: float
    nodes: int
    cutoffs: int
    tt_hits: int
    tt_misses: int
    leaf_evals: int
    pv: tuple[int, ...]

    @property
    def branching(self) -> float:
        """Average number of nodes per ply below this depth (1 when unmeasured)."""
        return self.nodes if self.nodes > 0 else 1.0


@dataclass(slots=True)
class SearchTrace:
    """Collector for deepening passes; bounded by ``max_records``."""

    max_records: int = 32
    records: list[DepthRecord] = field(default_factory=list)
    final_score: float = 0.0
    final_line: tuple[int, ...] = ()
    nodes: int = 0
    cutoffs: int = 0
    leaf_evals: int = 0

    def add(self, record: DepthRecord) -> DepthRecord:
        """Append a record, keeping the trace bounded."""
        if len(self.records) < self.max_records:
            self.records.append(record)
        self.final_score = record.score
        self.final_line = record.pv
        return record

    def record_for(self, depth: int) -> DepthRecord | None:
        """The record for ``depth``, if the trace kept it."""
        for record in reversed(self.records):
            if record.depth == depth:
                return record
        return None

    def clear(self) -> None:
        """Drop every record and reset the visit counters."""
        self.records.clear()
        self.final_score = 0.0
        self.final_line = ()
        self.nodes = 0
        self.cutoffs = 0
        self.leaf_evals = 0
