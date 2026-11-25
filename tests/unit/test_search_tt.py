"""Transposition table behaviour: bounds, capacity and statistics."""

from __future__ import annotations

import pytest

from chess_observatory.search.tt import Bound, TranspositionTable, TTEntry


def _entry(key: int, depth: int, value: float, move: int | None = None) -> TTEntry:
    return TTEntry(key=key, depth=depth, flag=Bound.EXACT, value=value, move=move)


def test_store_and_lookup_round_trip() -> None:
    table = TranspositionTable()
    entry = _entry(key=7, depth=4, value=12.5, move=1234)
    table.store(entry)
    assert table.lookup(7, 4) == entry
    assert table.size == 1
    assert table.stats == (1, 1, 0)


def test_lookup_returns_none_for_an_unstored_key() -> None:
    table = TranspositionTable()
    assert table.lookup(3, 2) is None
    assert table.stats == (0, 0, 1)


def test_lookup_requires_the_stored_depth() -> None:
    table = TranspositionTable()
    table.store(_entry(key=7, depth=2, value=1.0))
    assert table.lookup(7, 3) is None
    assert table.lookup(7, 1).depth == 2


def test_store_uses_bound_flags_and_moves() -> None:
    table = TranspositionTable()
    table.store(TTEntry(key=9, depth=3, flag=Bound.LOWER, value=90.0, move=88))
    found = table.lookup(9, 3)
    assert found is not None
    assert found.flag is Bound.LOWER
    assert found.move == 88


def test_capacity_evicts_when_exceeded() -> None:
    table = TranspositionTable(capacity=2)
    table.store(_entry(key=1, depth=1, value=1.0))
    table.store(_entry(key=2, depth=1, value=2.0))
    assert table.size == 2
    table.store(_entry(key=3, depth=1, value=3.0))
    assert table.size == 2


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError):
        TranspositionTable(capacity=0)


def test_clear_resets_entries_and_statistics() -> None:
    table = TranspositionTable()
    table.store(_entry(key=1, depth=1, value=1.0))
    assert table.size == 1
    table.clear()
    assert table.size == 0
    assert table.stats == (0, 0, 0)
