"""Square, bitboard and geometry tables."""

from __future__ import annotations

import pytest

from chess_observatory.core.squares import (
    BETWEEN,
    DARK_SQUARES,
    EDGES,
    FILE_A,
    FILE_H,
    FULL_BB,
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    LIGHT_SQUARES,
    LINE,
    RANK_1,
    RANK_8,
    RAYS,
    SQUARE_NAMES,
    Square,
    file_of,
    flip_file,
    flip_rank,
    lsb,
    make_square,
    msb,
    parse_square,
    popcount,
    rank_of,
    rotate_180,
    shift_east,
    shift_north,
    shift_north_east,
    shift_north_west,
    shift_south,
    shift_south_east,
    shift_south_west,
    shift_west,
    square_bb,
    square_distance,
    square_name,
    squares,
)


def test_all_square_names_round_trip() -> None:
    for square in range(64):
        assert parse_square(square_name(Square(square))) == square
    assert SQUARE_NAMES[0] == "a1"
    assert SQUARE_NAMES[63] == "h8"


def test_file_and_rank_helpers() -> None:
    assert (file_of(parse_square("a1")), rank_of(parse_square("a1"))) == (0, 0)
    assert (file_of(parse_square("h8")), rank_of(parse_square("h8"))) == (7, 7)
    assert make_square(4, 3) == parse_square("e4")
    with pytest.raises(ValueError):
        make_square(8, 0)
    with pytest.raises(ValueError):
        parse_square("i9")
    with pytest.raises(ValueError):
        parse_square("e")


def test_flips_and_rotation_are_involutions() -> None:
    for square in range(64):
        square = Square(square)
        assert flip_rank(flip_rank(square)) == square
        assert flip_file(flip_file(square)) == square
        assert rotate_180(rotate_180(square)) == square
        assert rotate_180(square) == flip_rank(flip_file(square))
        assert square_distance(square, square) == 0


def test_bit_helpers() -> None:
    bb = square_bb(parse_square("a1")) | square_bb(parse_square("h8"))
    assert popcount(bb) == 2
    assert lsb(bb) == parse_square("a1")
    assert msb(bb) == parse_square("h8")
    assert list(squares(bb)) == [parse_square("a1"), parse_square("h8")]
    assert popcount(FULL_BB) == 64
    assert popcount(LIGHT_SQUARES) == 32
    assert LIGHT_SQUARES | DARK_SQUARES == FULL_BB
    with pytest.raises(ValueError):
        lsb(0)
    with pytest.raises(ValueError):
        msb(0)


def test_shifts_never_wrap() -> None:
    for square in range(64):
        bit = square_bb(Square(square))
        for shifted in (
            shift_north(bit),
            shift_south(bit),
            shift_east(bit),
            shift_west(bit),
            shift_north_east(bit),
            shift_north_west(bit),
            shift_south_east(bit),
            shift_south_west(bit),
        ):
            assert shifted & ~FULL_BB == 0
            assert shifted.bit_count() <= 1
    assert shift_east(square_bb(parse_square("h1"))) == 0
    assert shift_west(square_bb(parse_square("a1"))) == 0
    assert shift_north_east(square_bb(parse_square("h8"))) == 0
    assert shift_north_west(square_bb(parse_square("a8"))) == 0


def test_edges_mask() -> None:
    assert EDGES == FILE_A | FILE_H | RANK_1 | RANK_8
    assert all(square_bb(Square(square)) & EDGES for square in list(range(8)) + list(range(56, 64)))


def test_knight_and_king_tables() -> None:
    assert len(KNIGHT_ATTACKS) == len(KING_ATTACKS) == 64
    assert popcount(KNIGHT_ATTACKS[0]) == 2
    assert popcount(KNIGHT_ATTACKS[parse_square("d4")]) == 8
    assert popcount(KING_ATTACKS[0]) == 3
    assert popcount(KING_ATTACKS[parse_square("d4")]) == 8
    # A knight never attacks its own square; neither does a king.
    for square in range(64):
        assert not KNIGHT_ATTACKS[square] & square_bb(Square(square))
        assert not KING_ATTACKS[square] & square_bb(Square(square))


def test_attack_tables_are_symmetric() -> None:
    for square in range(64):
        target = Square(square)
        for attacker in squares(KNIGHT_ATTACKS[square]):
            assert square_bb(target) & KNIGHT_ATTACKS[int(attacker)]
        for attacker in squares(KING_ATTACKS[square]):
            assert square_bb(target) & KING_ATTACKS[int(attacker)]
        assert KNIGHT_ATTACKS[int(flip_file(target))] == _flip_bb(KNIGHT_ATTACKS[square], 7)
        assert KNIGHT_ATTACKS[int(flip_rank(target))] == _flip_bb(KNIGHT_ATTACKS[square], 56)
        assert KING_ATTACKS[int(rotate_180(target))] == _flip_bb(KING_ATTACKS[square], 63)


def _flip_bb(bb: int, mask: int) -> int:
    result = 0
    for square in squares(bb):
        result |= square_bb(Square(int(square) ^ mask))
    return result


def test_rays_are_symmetric_and_do_not_include_origin() -> None:
    for direction, table in enumerate(RAYS):
        assert len(table) == 64
        for square in range(64):
            ray = table[square]
            assert not ray & square_bb(Square(square))
            for target in squares(ray):
                opposite = (direction + 4) % 8
                assert square_bb(Square(square)) & RAYS[opposite][int(target)]


def test_between_is_symmetric_and_exclusive() -> None:
    for a in range(64):
        for b in range(64):
            between = BETWEEN[a][b]
            assert between == BETWEEN[b][a]
            assert not between & square_bb(Square(a))
            assert not between & square_bb(Square(b))
    assert BETWEEN[int(parse_square("a1"))][int(parse_square("a8"))] == sum(
        square_bb(parse_square(f"a{rank}")) for rank in range(2, 8)
    )
    assert BETWEEN[int(parse_square("a1"))][int(parse_square("b3"))] == 0
    assert BETWEEN[int(parse_square("a1"))][int(parse_square("a1"))] == 0


def test_line_contains_both_squares_and_is_symmetric() -> None:
    for a in range(64):
        for b in range(64):
            line = LINE[a][b]
            assert line == LINE[b][a]
            if a == b:
                assert line == square_bb(Square(a))
            elif line:
                assert line & square_bb(Square(a))
                assert line & square_bb(Square(b))
    diagonal = LINE[int(parse_square("a1"))][int(parse_square("h8"))]
    assert diagonal == sum(
        square_bb(parse_square(f"{file}{rank}"))
        for file, rank in zip("abcdefgh", "12345678", strict=True)
    )
    assert LINE[int(parse_square("a1"))][int(parse_square("b3"))] == 0
