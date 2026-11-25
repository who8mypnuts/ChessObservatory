"""Own engine: negamax, alpha-beta, qsearch, mate scores, principal line, deepening."""

from __future__ import annotations

from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal
from chess_observatory.search.engine import SearchContext, iterative_deepening
from chess_observatory.search.limits import SearchLimits
from chess_observatory.search.tt import TranspositionTable

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _context(max_depth: int) -> SearchContext:
    return SearchContext(
        limits=SearchLimits(depth=max_depth),
        tt=TranspositionTable(capacity=4096),
        evaluate=lambda position: 0.0,
        max_depth=max_depth,
    )


def test_iterative_deepening_runs_one_step_per_depth() -> None:
    board = Board(parse_fen(START))
    score, _line, history = iterative_deepening(board, _context(2))
    assert [depth for depth, _score, _line in history] == [1, 2]
    assert history[0][0] == 1 and history[1][0] == 2
    assert history[1][1] == score
    assert len(history[0][2]) >= 1
    assert board.undo_depth == 0


def test_iterative_deepening_single_step_for_max_depth_one() -> None:
    board = Board(parse_fen(START))
    score, line, history = iterative_deepening(board, _context(1))
    assert [depth for depth, _score, _line in history] == [1]
    assert isinstance(score, float)
    assert isinstance(line, list)
    assert history[0][2]


def test_iterative_deepening_final_line_is_a_legal_move() -> None:
    board = Board(parse_fen(START))
    _score, line, _history = iterative_deepening(board, _context(2))
    assert line[0] in list(generate_legal(board))
