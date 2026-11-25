"""Packed move layout, flags and UCI conversion."""

from __future__ import annotations

import pytest

from chess_observatory.core.moves import (
    MOVE_NONE,
    MoveFlags,
    MoveList,
    move_flags,
    move_from,
    move_from_uci,
    move_is_capture,
    move_is_castle,
    move_is_double_push,
    move_is_en_passant,
    move_is_promotion,
    move_promotion,
    move_to,
    move_to_str,
    move_to_uci,
    pack_move,
    same_move,
)
from chess_observatory.core.pieces import PieceType
from chess_observatory.core.squares import Square, parse_square


def test_pack_and_accessors() -> None:
    move = pack_move(
        parse_square("e2"),
        parse_square("e4"),
        flags=MoveFlags.DOUBLE_PUSH,
    )
    assert move_from(move) == parse_square("e2")
    assert move_to(move) == parse_square("e4")
    assert move_promotion(move) is None
    assert move_flags(move) == MoveFlags.DOUBLE_PUSH
    assert move_is_double_push(move)
    assert not move_is_capture(move)
    assert not move_is_castle(move)
    assert not move_is_en_passant(move)
    assert not move_is_promotion(move)


def test_all_flag_bits_are_distinct() -> None:
    flags = [flag for flag in MoveFlags if flag is not MoveFlags.NONE]
    assert len(flags) == 5
    assert len({int(flag) for flag in flags}) == 5
    combined = MoveFlags.CAPTURE | MoveFlags.EN_PASSANT
    move = pack_move(Square(0), Square(0), flags=combined)
    assert move_flags(move) == combined
    assert move_is_capture(move)
    assert move_is_en_passant(move)


def test_promotion_encoding() -> None:
    for piece_type in (PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
        move = pack_move(
            parse_square("a7"),
            parse_square("a8"),
            promotion=piece_type,
            flags=MoveFlags.PROMOTION,
        )
        assert move_promotion(move) is piece_type
        assert move_is_promotion(move)
        assert move_to_uci(move) == f"a7a8{piece_type.letter.lower()}"


def test_uci_round_trip() -> None:
    for from_square in range(64):
        for to_square in range(64):
            move = pack_move(Square(from_square), Square(to_square))
            parsed = move_from_uci(move_to_uci(move))
            assert same_move(move, parsed)
    assert move_to_uci(MOVE_NONE) == "0000"
    assert move_from_uci("0000") == MOVE_NONE
    assert move_from_uci("E2E4") == pack_move(parse_square("e2"), parse_square("e4"))


def test_invalid_uci() -> None:
    for text in ("", "e2", "e2e9", "i2i4", "e7e8k", "e2e4x"):
        if text == "":
            assert move_from_uci(text) == MOVE_NONE
            continue
        with pytest.raises(ValueError):
            move_from_uci(text)


def test_same_move_ignores_flags_but_not_promotion() -> None:
    quiet = pack_move(parse_square("e2"), parse_square("e4"))
    flagged = pack_move(parse_square("e2"), parse_square("e4"), flags=MoveFlags.DOUBLE_PUSH)
    knight_promo = pack_move(parse_square("a7"), parse_square("a8"), promotion=PieceType.KNIGHT)
    queen_promo = pack_move(parse_square("a7"), parse_square("a8"), promotion=PieceType.QUEEN)
    assert same_move(quiet, flagged)
    assert not same_move(knight_promo, queen_promo)


def test_move_list_is_an_int_array() -> None:
    moves = MoveList()
    moves.append(pack_move(Square(0), Square(1)))
    moves.append(pack_move(Square(2), Square(3)))
    assert len(moves) == 2
    assert moves[0].bit_length() > 0
    assert isinstance(moves[0], int)
    moves.clear()
    assert len(moves) == 0


def test_readable_form() -> None:
    move = pack_move(parse_square("e2"), parse_square("e4"), flags=MoveFlags.DOUBLE_PUSH)
    assert "e2e4" in move_to_str(move)
    assert move_to_str(MOVE_NONE) == "0000"
