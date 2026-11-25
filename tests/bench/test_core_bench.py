"""Phase 1 hot-path benchmarks and the recorded baseline.

``tools/bench_core.py`` records ``tests/bench/baseline.json``; the tests here
keep the harness honest in CI (they run, and the baseline must describe the
metrics the tool actually measures). Comparing numbers against the baseline is a
local operation, because shared runners are not a stable measuring device::

    uv run python tools/bench_core.py --check
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from chess_observatory.core.attacks import attack_map, clear_attack_cache, see_ge
from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, perft
from chess_observatory.core.moves import MoveFlags, move_flags

pytestmark = pytest.mark.bench

TOOL = Path(__file__).resolve().parents[2] / "tools" / "bench_core.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bench_core_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bench_core = _load_tool()

START = bench_core.START
KIWIPETE = bench_core.KIWIPETE
MIDDLEGAME = bench_core.MIDDLEGAME


def test_perft_start_depth_3(benchmark) -> None:
    position = parse_fen(START)
    assert benchmark(lambda: perft(position, 3)) == 8902


def test_make_unmake_kiwipete(benchmark) -> None:
    board = Board(parse_fen(KIWIPETE))
    moves = list(generate_legal(board))

    def cycle() -> None:
        for move in moves:
            board.make(move)
            board.unmake()

    benchmark(cycle)
    assert board.undo_depth == 0
    assert board.is_consistent()


def test_attack_map_build(benchmark) -> None:
    position = parse_fen(MIDDLEGAME)

    def build() -> int:
        clear_attack_cache()
        return len(attack_map(position).checkers)

    assert benchmark(build) == 2


def test_see_over_captures(benchmark) -> None:
    position = parse_fen(KIWIPETE)
    captures = [move for move in generate_legal(position) if move_flags(move) & MoveFlags.CAPTURE]
    assert captures
    results = benchmark(lambda: [see_ge(position, move) for move in captures])
    assert len(results) == len(captures)


def test_baseline_describes_the_current_metrics() -> None:
    baseline = bench_core.load_baseline()
    assert baseline["schema"] == bench_core.SCHEMA
    assert baseline["python"]
    names = {name for name, _, _, _ in bench_core.METRICS}
    assert set(baseline["metrics"]) == names
    for name, entry in baseline["metrics"].items():
        assert entry["value"] > 0, name
        assert entry["unit"], name
        assert entry["note"], name


def test_check_reports_a_regression() -> None:
    baseline = {"metrics": {"perft.start.d4": {"value": 100.0, "unit": "nodes/s", "note": ""}}}
    current = {"metrics": {"perft.start.d4": {"value": 10.0, "unit": "nodes/s", "note": ""}}}
    assert bench_core.check(baseline, current)
    assert not bench_core.check(baseline, current, floor=0.05)
