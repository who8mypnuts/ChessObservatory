"""Differential oracle suite: the rules core against ``python-chess``.

The fast job runs a handful of random games on every CI push. The slow job runs
the 2,000-game CI gate. ``tools/differential.py`` is the same harness for the
100,000-game local run::

    uv run python tools/differential.py --games 100000 --san-sample 0

Every position compares the legal move set, terminal status, en-passant
availability and sampled SAN; every move compares the resulting FEN. A single
mismatch names the seed, game, ply, FEN and move, which is what makes a perft or
movegen regression diagnosable rather than merely red.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.differential

TOOL = Path(__file__).resolve().parents[2] / "tools" / "differential.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("differential_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


differential = _load_tool()


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_perft_matches_python_chess(depth: int) -> None:
    assert differential.compare_perft((depth,)) == len(differential.PERFT_POSITIONS)


def test_random_games_fast() -> None:
    stats = differential.compare_games(games=8, plies=100, seed=20261123)
    assert stats.positions > 0
    assert stats.san_compared > 0


def test_random_games_without_san_sampling() -> None:
    stats = differential.compare_games(games=4, plies=60, seed=11, san_sample=0)
    assert stats.san_compared == 0


@pytest.mark.slow
def test_random_games_two_thousand() -> None:
    stats = differential.compare_games(games=2000, plies=160, seed=7)
    assert stats.games == 2000


def test_pgn_import_matches_python_chess() -> None:
    differential.compare_pgn()


def test_harness_reports_a_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The harness must fail loudly, not silently pass, when a move is missing."""
    original = differential.generate_legal

    def broken(board: object) -> list[int]:
        moves = list(original(board))
        return moves[:-1] if moves else moves

    monkeypatch.setattr(differential, "generate_legal", broken)
    with pytest.raises(differential.DifferentialMismatch, match="legal moves differ"):
        differential.compare_games(games=1, plies=1, seed=1, san_sample=0)
