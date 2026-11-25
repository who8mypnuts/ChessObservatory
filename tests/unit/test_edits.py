"""Counterfactual edits and their legality reports."""

from __future__ import annotations

import chess
import pytest

from chess_observatory.core.edits import (
    LegalityReport,
    Relaxation,
    add_piece,
    clear_castling,
    inspect_position,
    null_move,
    relocate_piece,
    remove_piece,
    set_castling,
    set_ep,
    set_piece,
    set_side,
    swap_kings,
)
from chess_observatory.core.fen import parse_fen, to_fen
from chess_observatory.core.movegen import generate_legal
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.pieces import (
    BLACK_KING,
    WHITE_KING,
    WHITE_PAWN,
    WHITE_QUEEN,
    WHITE_ROOK,
    Color,
)
from chess_observatory.core.position import (
    CASTLE_BLACK_QUEEN,
    CASTLE_WHITE_KING,
)
from chess_observatory.core.squares import parse_square
from chess_observatory.errors import InvalidPositionError

START = chess.STARTING_FEN


def test_starting_position_is_legal() -> None:
    report = inspect_position(parse_fen(START))
    assert report == LegalityReport(legal=True, relaxed=frozenset(), notes=())
    assert report.describe() == "legal position"


def test_remove_piece_keeps_legal_positions_legal() -> None:
    position = parse_fen(START)
    edited, report = remove_piece(position, parse_square("d1"))
    assert report.legal
    assert edited.strict
    assert edited.piece_at(parse_square("d1")) == 0
    assert edited.is_consistent()
    assert position.piece_at(parse_square("d1")) == WHITE_QUEEN  # original untouched


def test_removing_a_king_is_reported() -> None:
    edited, report = remove_piece(parse_fen(START), parse_square("e1"))
    assert not report.legal
    assert Relaxation.MISSING_KING in report.relaxed
    assert not edited.strict
    assert edited.variant_note is not None
    assert "no white king" in edited.variant_note
    assert "missing_king" in report.to_dict()["relaxed"]


def test_adding_a_second_king_is_reported() -> None:
    edited, report = add_piece(parse_fen(START), parse_square("d1"), WHITE_KING, replace=True)
    assert Relaxation.MULTIPLE_KINGS in report.relaxed
    assert not edited.strict


def test_add_piece_refuses_occupied_squares_without_replace() -> None:
    with pytest.raises(InvalidPositionError):
        add_piece(parse_fen(START), parse_square("d1"), WHITE_QUEEN)
    edited, report = add_piece(parse_fen(START), parse_square("d1"), WHITE_ROOK, replace=True)
    assert edited.piece_at(parse_square("d1")) == WHITE_ROOK
    assert report.legal


def test_set_piece_zero_clears_the_square() -> None:
    edited, _ = set_piece(parse_fen(START), parse_square("a2"), 0)
    assert edited.piece_at(parse_square("a2")) == 0


def test_adjacent_kings_are_reported() -> None:
    position = parse_fen("8/8/8/8/8/4k3/8/4K3 w - - 0 1")
    edited, report = relocate_piece(position, parse_square("e1"), parse_square("e2"))
    assert Relaxation.ADJACENT_KINGS in report.relaxed
    assert not edited.strict


def test_relocating_from_an_empty_square_fails() -> None:
    with pytest.raises(InvalidPositionError):
        relocate_piece(parse_fen(START), parse_square("e4"), parse_square("e5"))


def test_pawn_on_back_rank_and_too_many_pawns() -> None:
    _, report = add_piece(parse_fen(START), parse_square("a8"), WHITE_PAWN, replace=True)
    assert Relaxation.PAWN_ON_BACK_RANK in report.relaxed
    assert Relaxation.TOO_MANY_PAWNS in report.relaxed


def test_too_many_pieces() -> None:
    position = parse_fen(START)
    for name in ("a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3"):
        position, _ = add_piece(position, parse_square(name), WHITE_QUEEN)
    _, report = add_piece(position, parse_square("a4"), WHITE_QUEEN)
    assert Relaxation.TOO_MANY_PIECES in report.relaxed


def test_castling_rights_without_rook_or_king() -> None:
    position = parse_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    _, report = remove_piece(position, parse_square("h1"))
    assert Relaxation.CASTLING_WITHOUT_ROOK in report.relaxed
    assert "h1" in report.describe()

    moved_king, _ = relocate_piece(position, parse_square("e1"), parse_square("e2"))
    moved_report = inspect_position(moved_king)
    assert Relaxation.CASTLING_WITHOUT_KING in moved_report.relaxed


def test_set_castling_and_clear_castling() -> None:
    position = parse_fen(START)
    cleared, report = clear_castling(position)
    assert cleared.castling == 0
    assert report.legal
    restored, _ = set_castling(cleared, CASTLE_WHITE_KING | CASTLE_BLACK_QUEEN)
    assert restored.castling == CASTLE_WHITE_KING | CASTLE_BLACK_QUEEN
    with pytest.raises(InvalidPositionError):
        set_castling(position, 0x80)


def test_set_side_can_leave_the_opponent_in_check() -> None:
    # Black rook e8 checks the white king; giving Black the move is illegal.
    position = parse_fen("4r2k/8/8/8/8/8/8/4K3 b - - 0 1", strict=False)
    assert Relaxation.SIDE_NOT_TO_MOVE_IN_CHECK in inspect_position(position).relaxed

    flipped, report = set_side(parse_fen(START), Color.BLACK)
    assert flipped.side is Color.BLACK
    assert flipped.ep is None
    assert report.legal


def test_set_ep_reports_wrong_rank_and_missing_pawn() -> None:
    position = parse_fen(START)
    _, wrong_rank = set_ep(position, parse_square("e3"))
    assert Relaxation.EN_PASSANT_ON_WRONG_RANK in wrong_rank.relaxed

    _, wrong_pawn = set_ep(position, parse_square("e6"))
    assert Relaxation.EN_PASSANT_WITHOUT_PAWN in wrong_pawn.relaxed

    _, clock = set_ep(position, parse_square("e6"))
    assert clock.legal is False

    slow_clock = parse_fen("4k3/8/8/4p3/8/8/8/4K3 w - - 5 1")
    _, clock_report = set_ep(slow_clock, parse_square("e6"))
    assert Relaxation.EN_PASSANT_WITHOUT_CLOCK in clock_report.relaxed


def test_set_ep_with_a_real_double_push_is_legal() -> None:
    position = parse_fen("4k3/8/8/8/4pP2/8/8/4K3 b - - 0 1")
    edited, report = set_ep(position, parse_square("f3"))
    assert report.legal
    assert to_fen(edited).split()[3] == "f3"


def test_null_move_flips_side_and_clocks() -> None:
    position = parse_fen(START)
    edited, report = null_move(position)
    assert edited.side is Color.BLACK
    assert edited.ep is None
    assert edited.halfmove == 1
    assert edited.fullmove == 1
    assert report.legal

    black_to_move = parse_fen("4k3/8/8/8/8/8/8/4K3 b - - 0 7")
    after, _ = null_move(black_to_move)
    assert after.side is Color.WHITE
    assert after.fullmove == 8


def test_swap_kings_exchanges_squares() -> None:
    position = parse_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    edited, report = swap_kings(position)
    assert edited.piece_at(parse_square("e1")) == BLACK_KING
    assert edited.piece_at(parse_square("e8")) == WHITE_KING
    assert report.legal
    assert edited.is_consistent()


def test_non_strict_positions_still_generate_moves() -> None:
    # No black king: the report says so, but White's moves are still sane.
    position = parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False)
    moves = generate_legal(position)
    assert "e1e2" in {move_to_uci(move) for move in moves}
    assert position.strict is False


def test_edited_position_matches_python_chess_when_legal() -> None:
    position = parse_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    edited, _ = remove_piece(position, parse_square("a1"))
    edited, report = clear_castling(edited)
    assert report.legal
    oracle = chess.Board(edited_fen := to_fen(edited))
    ours = {move_to_uci(move) for move in generate_legal(edited)}
    assert ours == {move.uci() for move in oracle.legal_moves}
    assert "a1" not in edited_fen


def test_report_serialises() -> None:
    _, report = remove_piece(parse_fen(START), parse_square("e1"))
    payload = report.to_dict()
    assert payload["legal"] is False
    assert "missing_king" in payload["relaxed"]
    assert payload["notes"]


def test_removing_an_empty_square_is_a_no_op() -> None:
    position = parse_fen(START)
    edited, report = remove_piece(position, parse_square("e4"))
    assert edited == position
    assert report.legal


def test_swap_kings_with_a_missing_king_is_a_no_op() -> None:
    position = parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False)
    edited, report = swap_kings(position)
    assert edited.mailbox == position.mailbox
    assert Relaxation.MISSING_KING in report.relaxed


def test_piece_belongs_to_helper() -> None:
    from chess_observatory.core.edits import piece_belongs_to

    assert piece_belongs_to(WHITE_PAWN, Color.WHITE)
    assert not piece_belongs_to(WHITE_PAWN, Color.BLACK)
    assert not piece_belongs_to(0, Color.WHITE)
