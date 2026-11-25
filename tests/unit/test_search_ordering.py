"""Move ordering heuristics: TT move, MVV-LVA, promotions, killers, history, countermoves."""

from __future__ import annotations

from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.squares import parse_square
from chess_observatory.search.ordering import order_moves, score_move

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
CAPTURE_POSITION = "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1"
PROMOTION_POSITION = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"


def _legal(fen: str = START) -> list[int]:
    return list(generate_legal(Board(parse_fen(fen))))


def _move_with_tag(fen: str, tag: str) -> int:
    for move in _legal(fen):
        if tag in move_to_uci(move):
            return move
    raise AssertionError(f"no move tagged {tag}")


def _capture(fen: str = CAPTURE_POSITION) -> int:
    return _move_with_tag(fen, "e4d5")


def test_quiet_moves_score_zero_and_keep_stable_order() -> None:
    moves = _legal()
    scores = [score_move(Board(parse_fen(START)), move) for move in moves]
    assert scores == sorted(scores, reverse=True)
    assert order_moves(Board(parse_fen(START)), moves) == moves


def test_transposition_table_move_is_searched_first() -> None:
    moves = _legal()
    tt_move = _move_with_tag(START, "g1f3")
    assert order_moves(Board(parse_fen(START)), moves, tt_move=tt_move)[0] == tt_move


def test_mvv_lva_prefers_the_most_valuable_victim() -> None:
    moves = _legal(CAPTURE_POSITION)
    capture = _capture()
    quiet = _move_with_tag(CAPTURE_POSITION, "e4e5")
    assert score_move(Board(parse_fen(CAPTURE_POSITION)), capture) > score_move(
        Board(parse_fen(CAPTURE_POSITION)), quiet
    )
    ordered = order_moves(Board(parse_fen(CAPTURE_POSITION)), moves, see_order_bonus=10.0)
    assert ordered[0] == capture


def test_promotion_scores_above_a_quiet_move() -> None:
    moves = _legal(PROMOTION_POSITION)
    promotion = _move_with_tag(PROMOTION_POSITION, "a7a8")
    assert promotion in moves
    assert score_move(Board(parse_fen(PROMOTION_POSITION)), promotion) > 0.0
    ordered = order_moves(Board(parse_fen(PROMOTION_POSITION)), moves)
    assert ordered[0] == promotion


def test_killer_moves_score_first() -> None:
    board = Board(parse_fen(CAPTURE_POSITION))
    quiet = _move_with_tag(CAPTURE_POSITION, "e4e5")
    killer_origin = int(quiet) & 0x3F
    assert score_move(board, quiet, killers=(killer_origin,)) > score_move(board, quiet)


def test_history_and_countermoves_adjust_the_score() -> None:
    board = Board(parse_fen(START))
    e2e4 = _move_with_tag(START, "e2e4")
    assert score_move(board, e2e4, history={e2e4: 400}) > score_move(board, e2e4)
    assert score_move(board, e2e4, countermoves={e2e4: 250}) > score_move(board, e2e4)


def test_promotion_move_is_the_promoted_piece() -> None:
    promotion = _move_with_tag(PROMOTION_POSITION, "a7a8")
    assert promotion in _legal(PROMOTION_POSITION)
    assert parse_square("a8") == (promotion >> 6) & 0x7F
