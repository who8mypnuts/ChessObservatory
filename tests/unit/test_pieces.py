"""Piece encoding and character maps."""

from __future__ import annotations

import pytest

from chess_observatory.core.pieces import (
    BLACK_BISHOP,
    BLACK_KING,
    BLACK_KNIGHT,
    BLACK_PAWN,
    BLACK_QUEEN,
    BLACK_ROOK,
    CHAR_TO_PIECE,
    NO_PIECE,
    PIECE_TO_CHAR,
    PIECES,
    WHITE_BISHOP,
    WHITE_KING,
    WHITE_KNIGHT,
    WHITE_PAWN,
    WHITE_QUEEN,
    WHITE_ROOK,
    Color,
    PieceType,
    color_of,
    index_color,
    index_piece,
    index_type,
    make_piece,
    piece_from_char,
    piece_index,
    piece_to_char,
    type_of,
)


def test_piece_round_trip() -> None:
    for color in Color:
        for piece_type in PieceType:
            piece = make_piece(color, piece_type)
            assert color_of(piece) is color
            assert type_of(piece) is piece_type


def test_piece_values_are_stable() -> None:
    assert [int(piece) for piece in PIECES] == [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]
    assert (WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING) == (
        1,
        2,
        3,
        4,
        5,
        6,
    )
    assert (BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP, BLACK_ROOK, BLACK_QUEEN, BLACK_KING) == (
        9,
        10,
        11,
        12,
        13,
        14,
    )


def test_char_maps_are_inverse() -> None:
    for piece, char in PIECE_TO_CHAR.items():
        assert CHAR_TO_PIECE[char] == piece
        assert piece_to_char(piece) == char
        assert piece_from_char(char) == piece
    assert piece_to_char(NO_PIECE) == "."
    assert len(set(PIECE_TO_CHAR.values())) == 12


def test_color_properties() -> None:
    assert Color.WHITE.opposite is Color.BLACK
    assert Color.BLACK.opposite is Color.WHITE
    assert Color.WHITE.sign == 1
    assert Color.BLACK.sign == -1
    assert Color.WHITE.name == "white"
    assert Color.BLACK.name == "black"


def test_piece_type_properties() -> None:
    assert [piece_type.letter for piece_type in PieceType] == list("PNBRQK")
    assert PieceType.PAWN.name == "pawn"
    assert PieceType.KING.name == "king"


def test_index_helpers() -> None:
    seen = set()
    for color in Color:
        for piece_type in PieceType:
            index = piece_index(color, piece_type)
            assert 0 <= index < 12
            seen.add(index)
            assert index_color(index) is color
            assert index_type(index) is piece_type
            assert index_piece(index) == make_piece(color, piece_type)
    assert seen == set(range(12))


def test_empty_piece_has_no_colour_or_type() -> None:
    with pytest.raises(ValueError):
        color_of(NO_PIECE)
    with pytest.raises(ValueError):
        type_of(NO_PIECE)
    with pytest.raises(ValueError):
        piece_from_char("x")
