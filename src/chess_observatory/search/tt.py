"""Transposition table with bounds and capacity control (Phase 2, step 3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Bound(StrEnum):
    """Search bound carried by a stored entry."""

    EXACT = "exact"
    LOWER = "lower"
    UPPER = "upper"


@dataclass(frozen=True, slots=True)
class TTEntry:
    """One stored result: the position key it belongs to, depth, bound and value."""

    key: int
    depth: int
    flag: Bound
    value: float
    move: int | None = None


class TranspositionTable:
    """Bounded transposition table keyed by position key, keeping the deepest entry."""

    __slots__ = ("_capacity", "_entries", "_hits", "_misses", "_stores")

    def __init__(self, capacity: int = 256) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._entries: dict[int, TTEntry] = {}
        self._capacity = capacity
        self._stores = 0
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Number of live entries."""
        return len(self._entries)

    @property
    def stats(self) -> tuple[int, int, int]:
        """``(stores, hits, misses)`` since construction."""
        return (self._stores, self._hits, self._misses)

    def lookup(self, key: int, depth: int) -> TTEntry | None:
        """Return the deepest stored entry for ``key`` when it is at least ``depth`` plies deep."""
        entry = self._entries.get(key)
        if entry is not None and entry.depth >= depth:
            self._hits += 1
            return entry
        self._misses += 1
        return None

    def store(self, entry: TTEntry) -> None:
        """Insert an entry, evicting the oldest entry when the capacity is exceeded."""
        self._entries[entry.key] = entry
        self._stores += 1
        if len(self._entries) > self._capacity:
            self._entries.pop(next(iter(self._entries)))

    def clear(self) -> None:
        """Drop every entry and reset statistics."""
        self._entries.clear()
        self._stores = 0
        self._hits = 0
        self._misses = 0
