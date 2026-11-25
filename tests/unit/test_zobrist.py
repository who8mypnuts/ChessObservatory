"""Zobrist keys: stability, sensitivity and the splitmix64 generator."""

from __future__ import annotations

from chess_observatory.core.pieces import Color, piece_from_char
from chess_observatory.core.position import CASTLE_ALL, Position
from chess_observatory.core.squares import make_square, parse_square
from chess_observatory.core.zobrist import (
    CASTLING_KEYS,
    EP_FILE_KEYS,
    PIECE_KEYS,
    SIDE_KEY,
    compute_key,
    splitmix64,
    variant_key,
)

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


def test_splitmix64_matches_the_published_vector() -> None:
    state, value = splitmix64(0)
    assert state == 0x9E3779B97F4A7C15
    assert value == 0xE220A8397B1DCDAF


def test_tables_have_the_right_shape_and_are_nonzero() -> None:
    assert len(PIECE_KEYS) == 12
    assert all(len(row) == 64 for row in PIECE_KEYS)
    assert len(CASTLING_KEYS) == 16
    assert len(EP_FILE_KEYS) == 8
    assert SIDE_KEY != 0
    assert all(key != 0 for row in PIECE_KEYS for key in row)


def test_key_is_deterministic() -> None:
    position = position_from_rows(STARTING_ROWS)
    assert compute_key(position) == compute_key(position)
    assert compute_key(position) == compute_key(Position.from_pieces(position.piece_map()))


def test_key_is_sensitive_to_every_field() -> None:
    position = position_from_rows(STARTING_ROWS)
    base = compute_key(position)
    assert compute_key(position.copy(side=Color.BLACK)) != base
    assert compute_key(position.copy(castling=CASTLE_ALL)) != base
    assert compute_key(position.copy(ep=parse_square("e3"))) != base
    assert compute_key(position.copy(ep=parse_square("d3"))) != compute_key(
        position.copy(ep=parse_square("e3"))
    )


def test_key_changes_when_a_piece_moves() -> None:
    position = position_from_rows(STARTING_ROWS)
    pieces = position.piece_map()
    pawn = pieces.pop(parse_square("e2"))
    pieces[parse_square("e4")] = pawn
    moved = Position.from_pieces(pieces)
    assert compute_key(moved) != compute_key(position)


def test_variant_key_distinguishes_relaxations() -> None:
    position = position_from_rows(STARTING_ROWS)
    assert variant_key(position) == (True, "")
    relaxed = position.copy(strict=False, variant_note="missing black king")
    assert variant_key(relaxed) == (False, "missing black king")
