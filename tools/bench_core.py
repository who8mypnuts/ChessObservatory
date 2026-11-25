#!/usr/bin/env python3
"""Record and check the Phase 1 performance baseline.

    uv run python tools/bench_core.py            # measure and print
    uv run python tools/bench_core.py --write    # measure and rewrite baseline
    uv run python tools/bench_core.py --check    # fail if below 50 % of baseline

The numbers are machine-specific. The committed ``tests/bench/baseline.json``
exists so a hot-path change has a recorded number to argue with, and so a local
``--check`` catches an accidental order-of-magnitude regression. CI runs the
schema test only, because shared runners are not a stable measuring device.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from chess_observatory.core.attacks import attack_map, clear_attack_cache, see_ge
from chess_observatory.core.fen import parse_fen, to_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, perft
from chess_observatory.core.moves import MoveFlags, move_flags
from chess_observatory.core.san import to_san

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "bench" / "baseline.json"
SCHEMA = 1

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
MIDDLEGAME = "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"


def _rate(operation: Callable[[], object], *, units: int = 1, minimum: float = 0.25) -> float:
    """Units per second, after a warm-up, measured over at least ``minimum`` s."""
    operation()
    count = 0
    started = time.perf_counter()
    while time.perf_counter() - started < minimum:
        operation()
        count += 1
    return count * units / (time.perf_counter() - started)


def _perft_nodes_per_second(fen: str, depth: int) -> float:
    position = parse_fen(fen)
    nodes = perft(position, depth)
    perft(position, depth)  # warm-up
    started = time.perf_counter()
    perft(position, depth)
    elapsed = time.perf_counter() - started
    return nodes / elapsed


def _make_unmake_rate(fen: str) -> float:
    board = Board(parse_fen(fen))
    moves = list(generate_legal(board))

    def cycle() -> None:
        for move in moves:
            board.make(move)
            board.unmake()

    return _rate(cycle, units=len(moves))


def _attack_map_rate(fen: str) -> float:
    position = parse_fen(fen)

    def build() -> None:
        clear_attack_cache()
        attack_map(position)

    return _rate(build)


def _see_rate(fen: str) -> float:
    position = parse_fen(fen)
    captures = [move for move in generate_legal(position) if move_flags(move) & MoveFlags.CAPTURE]

    def evaluate() -> None:
        for move in captures:
            see_ge(position, move)

    return _rate(evaluate, units=len(captures))


def _san_rate(fen: str) -> float:
    board = Board(parse_fen(fen))
    moves = list(generate_legal(board))

    def render() -> None:
        for move in moves:
            to_san(board, move)

    return _rate(render, units=len(moves))


def _fen_rate(fen: str) -> float:
    position = parse_fen(fen)
    return _rate(lambda: to_fen(position))


METRICS: tuple[tuple[str, str, str, Callable[[], float]], ...] = (
    (
        "perft.start.d4",
        "nodes/s",
        "perft from the starting position at depth 4",
        lambda: _perft_nodes_per_second(START, 4),
    ),
    (
        "make_unmake.kiwipete",
        "move pairs/s",
        "make then unmake every legal move in kiwipete",
        lambda: _make_unmake_rate(KIWIPETE),
    ),
    (
        "attack_map.middlegame",
        "maps/s",
        "cold attack map build (cache cleared each time)",
        lambda: _attack_map_rate(MIDDLEGAME),
    ),
    (
        "see.kiwipete",
        "moves/s",
        "static exchange evaluation over every legal capture",
        lambda: _see_rate(KIWIPETE),
    ),
    (
        "san.kiwipete",
        "moves/s",
        "canonical SAN generation for every legal move",
        lambda: _san_rate(KIWIPETE),
    ),
    (
        "fen.middlegame",
        "positions/s",
        "canonical FEN emission",
        lambda: _fen_rate(MIDDLEGAME),
    ),
)


def measure() -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name, unit, note, operation in METRICS:
        metrics[name] = {"value": round(operation(), 1), "unit": unit, "note": note}
    return {
        "schema": SCHEMA,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "metrics": metrics,
    }


def load_baseline(path: Path = BASELINE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(baseline: dict[str, Any], current: dict[str, Any], floor: float = 0.5) -> list[str]:
    """Return a list of regressions below ``floor`` times the baseline value."""
    problems: list[str] = []
    for name, entry in baseline["metrics"].items():
        if name not in current["metrics"]:
            problems.append(f"{name}: missing from the current run")
            continue
        expected = entry["value"]
        actual = current["metrics"][name]["value"]
        if expected and actual < expected * floor:
            problems.append(
                f"{name}: {actual:.1f} {entry['unit']} is below "
                f"{floor:.0%} of baseline {expected:.1f}"
            )
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the baseline file")
    parser.add_argument("--check", action="store_true", help="compare against the baseline")
    parser.add_argument("--json", action="store_true", help="print the measurement as JSON")
    args = parser.parse_args(argv)

    current = measure()
    if args.json:
        print(json.dumps(current, indent=2))
    else:
        print(f"python {current['python']} on {current['platform']}")
        for name, entry in current["metrics"].items():
            print(f"  {name:28} {entry['value']:12,.1f} {entry['unit']}")

    if args.write:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE.relative_to(ROOT)}")

    if args.check:
        baseline = load_baseline()
        problems = check(baseline, current)
        if problems:
            print("regressions:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1
        print("all metrics within 50 % of the baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
