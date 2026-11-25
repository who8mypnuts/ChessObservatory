"""Own engine: negamax, alpha-beta, qsearch, mate scores, principal line."""

from __future__ import annotations

from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, in_check, legal_move_from_uci
from chess_observatory.core.moves import move_to
from chess_observatory.core.squares import parse_square
from chess_observatory.search.engine import MATE_SCORE, SearchContext, negamax, qsearch, search
from chess_observatory.search.limits import SearchLimits
from chess_observatory.search.tt import TranspositionTable

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MATE_POSITION = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"


def _context() -> SearchContext:
    return SearchContext(
        limits=SearchLimits(depth=2),
        tt=TranspositionTable(capacity=4096),
        evaluate=lambda position: 0.0,
        max_depth=2,
    )


def _move_of(move: int) -> int:
    return int(move_to(move))


def test_qsearch_reports_mate_for_an_checkmated_side_to_move() -> None:
    board = Board(parse_fen(MATE_POSITION))
    board.make(legal_move_from_uci(board, "a1a8"))
    assert in_check(board)
    score = qsearch(board, float("-inf"), float("inf"), ply=1, ctx=_context())
    assert score == -MATE_SCORE + 1


def test_search_finds_mate_in_one() -> None:
    board = Board(parse_fen(MATE_POSITION))
    score, line = search(board, _context())
    assert score > 0.0
    assert len(line) == 1
    assert _move_of(line[0]) == parse_square("a8")


def test_search_on_the_start_position_returns_a_legal_principal_line() -> None:
    board = Board(parse_fen(START))
    score, line = search(board, _context())
    assert isinstance(score, float)
    assert line
    assert line[0] in list(generate_legal(board))
    assert board.undo_depth == 0


def test_negamax_returns_a_float_score() -> None:
    board = Board(parse_fen(START))
    assert isinstance(negamax(board, float("-inf"), float("inf"), 2, 0, _context()), float)


def test_transposition_table_is_reused_across_searches() -> None:
    board = Board(parse_fen(START))
    ctx = _context()
    first_score, _first_line = search(board, ctx)
    second_score, _second_line = search(board, ctx)
    stores, hits, _misses = ctx.tt.stats
    assert stores > 0
    assert hits > 0
    assert first_score == second_score
    assert board.undo_depth == 0


def test_evaluate_uses_the_context_value() -> None:
    ctx = _context()
    board = Board(parse_fen(START))
    assert ctx.evaluate(board) == 0.0
