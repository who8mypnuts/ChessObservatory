"""Immutable position snapshot and its invariants."""

from __future__ import annotations

from dataclasses import replace

import pytest

from chess_observatory.core.pieces import (
    BLACK_BISHOP,
    BLACK_KING,
    BLACK_KNIGHT,
    BLACK_PAWN,
    BLACK_QUEEN,
    BLACK_ROOK,
    WHITE_BISHOP,
    WHITE_KING,
    WHITE_KNIGHT,
    WHITE_PAWN,
    WHITE_QUEEN,
    WHITE_ROOK,
    Color,
    PieceType,
    piece_from_char,
)
from chess_observatory.core.position import (
    CASTLE_ALL,
    Position,
    piece_at_index,
)
from chess_observatory.core.squares import Square, make_square, parse_square, square_bb

STARTING_ROWS = (
    "rnbqkbnr",
    "pppppppp",
    "........",
    "........",
    "........",
    "........",
    "PPPPPPPP",
    "RNBQKBNR",
)


def position_from_rows(rows: tuple[str, ...], *, side: Color = Color.WHITE) -> Position:
    pieces = {}
    for rank_index, row in enumerate(reversed(rows)):
        for file_index, char in enumerate(row):
            if char != ".":
                pieces[make_square(file_index, rank_index)] = piece_from_char(char)
    return Position.from_pieces(pieces, side=side)


def test_starting_position_shape() -> None:
    position = position_from_rows(STARTING_ROWS)
    assert position.is_consistent()
    assert position.occupancy.bit_count() == 32
    assert position.color_occupancy(Color.WHITE).bit_count() == 16
    assert position.color_occupancy(Color.BLACK).bit_count() == 16
    assert position.king_square(Color.WHITE) == parse_square("e1")
    assert position.king_square(Color.BLACK) == parse_square("e8")
    assert position.piece_at(parse_square("e1")) == WHITE_KING
    assert position.piece_at(parse_square("e8")) == BLACK_KING
    assert position.piece_at(parse_square("e4")) == 0
    assert position.is_empty(parse_square("e4"))
    assert position.has_piece(parse_square("e2"))


def test_piece_lookup_by_type_and_colour() -> None:
    position = position_from_rows(STARTING_ROWS)
    assert position.pieces(Color.WHITE, PieceType.PAWN) == 0x000000000000FF00
    assert position.pieces(Color.BLACK, PieceType.PAWN) == 0x00FF000000000000
    assert position.pieces(Color.WHITE, PieceType.KNIGHT) == (
        square_bb(parse_square("b1")) | square_bb(parse_square("g1"))
    )
    assert len(position.piece_map()) == 32
    assert len(position.piece_list(Color.WHITE)) == 16
    assert len(position.piece_list(Color.BLACK)) == 16


def test_specific_pieces_are_where_expected() -> None:
    position = position_from_rows(STARTING_ROWS)
    assert position.piece_at(parse_square("a1")) == WHITE_ROOK
    assert position.piece_at(parse_square("b1")) == WHITE_KNIGHT
    assert position.piece_at(parse_square("c1")) == WHITE_BISHOP
    assert position.piece_at(parse_square("d1")) == WHITE_QUEEN
    assert position.piece_at(parse_square("a8")) == BLACK_ROOK
    assert position.piece_at(parse_square("b8")) == BLACK_KNIGHT
    assert position.piece_at(parse_square("c8")) == BLACK_BISHOP
    assert position.piece_at(parse_square("d8")) == BLACK_QUEEN
    assert position.piece_at(parse_square("a2")) == WHITE_PAWN
    assert position.piece_at(parse_square("a7")) == BLACK_PAWN


def test_copy_is_a_new_value() -> None:
    position = position_from_rows(STARTING_ROWS)
    changed = position.copy(side=Color.BLACK)
    assert position.side is Color.WHITE
    assert changed.side is Color.BLACK
    assert changed.copy(side=Color.WHITE) == position


def test_castling_helpers() -> None:
    position = position_from_rows(STARTING_ROWS).copy(castling=CASTLE_ALL)
    assert position.can_castle(Color.WHITE, kingside=True)
    assert position.can_castle(Color.WHITE, kingside=False)
    assert position.can_castle(Color.BLACK, kingside=True)
    assert position.can_castle(Color.BLACK, kingside=False)
    none = position.copy(castling=0)
    assert not none.can_castle(Color.WHITE, kingside=True)


def test_empty_position() -> None:
    position = Position.empty()
    assert position.occupancy == 0
    assert position.is_consistent()
    assert position.king_square(Color.WHITE) is None
    assert position.king_square(Color.BLACK) is None
    assert position.fullmove == 1


def test_invalid_shapes_are_rejected() -> None:
    good = position_from_rows(STARTING_ROWS)
    with pytest.raises(ValueError):
        replace(good, bb=(0,) * 11)
    with pytest.raises(ValueError):
        replace(good, mailbox=bytes(63))
    with pytest.raises(ValueError):
        replace(good, castling=16)
    with pytest.raises(ValueError):
        replace(good, ep=Square(64))
    with pytest.raises(ValueError):
        replace(good, halfmove=-1)
    with pytest.raises(ValueError):
        replace(good, bb=(1, 1, *good.bb[2:]))


def test_overlapping_bitboards_are_rejected() -> None:
    with pytest.raises(ValueError):
        Position(
            bb=(1, 1) + (0,) * 10,
            mailbox=bytes(64),
            side=Color.WHITE,
            castling=0,
            ep=None,
            halfmove=0,
            fullmove=1,
        )


def test_consistency_detects_mailbox_drift() -> None:
    position = position_from_rows(STARTING_ROWS)
    tampered = replace(position, mailbox=bytes(64))
    assert not tampered.is_consistent()


def test_text_rendering() -> None:
    text = str(position_from_rows(STARTING_ROWS))
    assert text.splitlines()[0] == "8 r n b q k b n r"
    assert text.splitlines()[-1] == "  a b c d e f g h"


def test_invalid_field_types_are_rejected() -> None:
    with pytest.raises(ValueError):
        replace(position_from_rows(STARTING_ROWS), side="white")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(position_from_rows(STARTING_ROWS), bb=(1 << 64,) + (0,) * 11)
    with pytest.raises(ValueError):
        replace(position_from_rows(STARTING_ROWS), castling=0x10)
    with pytest.raises(ValueError):
        replace(position_from_rows(STARTING_ROWS), ep=Square(64))


def test_from_pieces_skips_empty_entries() -> None:
    position = Position.from_pieces({Square(0): 0, Square(4): WHITE_KING})
    assert position.piece_at(Square(4)) == WHITE_KING
    assert position.occupied == position.occupancy
    assert piece_at_index(0) == 1


def test_king_square_is_none_when_missing() -> None:
    position = Position.from_pieces({}, strict=False)
    assert position.king_square(Color.WHITE) is None


def test_is_consistent_rejects_bad_mailbox_bytes() -> None:
    position = position_from_rows(STARTING_ROWS)
    tampered = replace(position, mailbox=bytes([7]) + bytes(63))
    assert not tampered.is_consistent()
