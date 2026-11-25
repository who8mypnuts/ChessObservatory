"""Squares, bitboards and precomputed geometry (plan Phase 1, step 1).

Conventions, fixed for the whole project:

* square ``0`` is ``a1`` and square ``63`` is ``h8``;
* a bitboard is a Python ``int`` with bit ``n`` set for square ``n``;
* files and ranks are zero-based internally and one-based in notation.

Everything here is pure data and pure functions. The tables are built once at
import time and never mutated, so they are safe to share across threads.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Final, NewType

Square = NewType("Square", int)
Bitboard = int

FULL_BB: Final = (1 << 64) - 1

FILE_A: Final = 0x0101010101010101
FILE_B: Final = FILE_A << 1
FILE_C: Final = FILE_A << 2
FILE_D: Final = FILE_A << 3
FILE_E: Final = FILE_A << 4
FILE_F: Final = FILE_A << 5
FILE_G: Final = FILE_A << 6
FILE_H: Final = FILE_A << 7

FILES: Final = (FILE_A, FILE_B, FILE_C, FILE_D, FILE_E, FILE_F, FILE_G, FILE_H)

RANK_1: Final = 0x00000000000000FF
RANK_2: Final = RANK_1 << 8
RANK_3: Final = RANK_1 << 16
RANK_4: Final = RANK_1 << 24
RANK_5: Final = RANK_1 << 32
RANK_6: Final = RANK_1 << 40
RANK_7: Final = RANK_1 << 48
RANK_8: Final = RANK_1 << 56

RANKS: Final = (
    RANK_1,
    RANK_2,
    RANK_3,
    RANK_4,
    RANK_5,
    RANK_6,
    RANK_7,
    RANK_8,
)

EDGES: Final = FILE_A | FILE_H | RANK_1 | RANK_8
LIGHT_SQUARES: Final = 0x55AA55AA55AA55AA
DARK_SQUARES: Final = FULL_BB ^ LIGHT_SQUARES

# Directions in clockwise order starting north. Opposite directions differ by 4.
NORTH: Final = 0
NORTH_EAST: Final = 1
EAST: Final = 2
SOUTH_EAST: Final = 3
SOUTH: Final = 4
SOUTH_WEST: Final = 5
WEST: Final = 6
NORTH_WEST: Final = 7

DIRECTIONS: Final = (NORTH, NORTH_EAST, EAST, SOUTH_EAST, SOUTH, SOUTH_WEST, WEST, NORTH_WEST)
DIRECTION_DELTAS: Final[tuple[tuple[int, int], ...]] = (
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
)

FILE_NAMES: Final = "abcdefgh"
RANK_NAMES: Final = "12345678"
SQUARE_NAMES: Final = tuple(
    f"{FILE_NAMES[file_index]}{RANK_NAMES[rank_index]}"
    for rank_index in range(8)
    for file_index in range(8)
)

assert len(SQUARE_NAMES) == 64


def make_square(file_index: int, rank_index: int) -> Square:
    """Build a square from zero-based file and rank, validating both."""
    if not (0 <= file_index < 8 and 0 <= rank_index < 8):
        raise ValueError(f"square out of range: file={file_index}, rank={rank_index}")
    return Square(rank_index * 8 + file_index)


def file_of(square: Square) -> int:
    return int(square) & 7


def rank_of(square: Square) -> int:
    return int(square) >> 3


def square_name(square: Square) -> str:
    return SQUARE_NAMES[int(square)]


def parse_square(name: str) -> Square:
    """Parse coordinate notation such as ``e4``."""
    if len(name) != 2 or name[0] not in FILE_NAMES or name[1] not in RANK_NAMES:
        raise ValueError(f"not a square: {name!r}")
    return make_square(FILE_NAMES.index(name[0]), RANK_NAMES.index(name[1]))


def square_bb(square: Square) -> Bitboard:
    return 1 << int(square)


def flip_rank(square: Square) -> Square:
    """Mirror a square vertically (a1 <-> a8)."""
    return Square(int(square) ^ 56)


def flip_file(square: Square) -> Square:
    """Mirror a square horizontally (a1 <-> h1)."""
    return Square(int(square) ^ 7)


def rotate_180(square: Square) -> Square:
    return Square(int(square) ^ 63)


def square_distance(a: Square, b: Square) -> int:
    """Chebyshev distance, the number of king moves between two squares."""
    return max(abs(file_of(a) - file_of(b)), abs(rank_of(a) - rank_of(b)))


def squares(bb: Bitboard) -> Iterator[Square]:
    """Yield each set square in ascending order."""
    while bb:
        bit = bb & -bb
        yield Square(bit.bit_length() - 1)
        bb ^= bit


def popcount(bb: Bitboard) -> int:
    return bb.bit_count()


def lsb(bb: Bitboard) -> Square:
    """Least significant set square. The caller guarantees a non-empty board."""
    if not bb:
        raise ValueError("lsb of an empty bitboard")
    return Square((bb & -bb).bit_length() - 1)


def msb(bb: Bitboard) -> Square:
    """Most significant set square. The caller guarantees a non-empty board."""
    if not bb:
        raise ValueError("msb of an empty bitboard")
    return Square(bb.bit_length() - 1)


def shift_north(bb: Bitboard) -> Bitboard:
    return (bb << 8) & FULL_BB


def shift_south(bb: Bitboard) -> Bitboard:
    return bb >> 8


def shift_east(bb: Bitboard) -> Bitboard:
    return (bb & ~FILE_H) << 1


def shift_west(bb: Bitboard) -> Bitboard:
    return (bb & ~FILE_A) >> 1


def shift_north_east(bb: Bitboard) -> Bitboard:
    return ((bb & ~FILE_H) << 9) & FULL_BB


def shift_north_west(bb: Bitboard) -> Bitboard:
    return ((bb & ~FILE_A) << 7) & FULL_BB


def shift_south_east(bb: Bitboard) -> Bitboard:
    return (bb & ~FILE_H) >> 7


def shift_south_west(bb: Bitboard) -> Bitboard:
    return (bb & ~FILE_A) >> 9


SHIFTS: Final = (
    shift_north,
    shift_north_east,
    shift_east,
    shift_south_east,
    shift_south,
    shift_south_west,
    shift_west,
    shift_north_west,
)


def _build_ray(square: Square, file_delta: int, rank_delta: int) -> Bitboard:
    result = 0
    file_index = file_of(square) + file_delta
    rank_index = rank_of(square) + rank_delta
    while 0 <= file_index < 8 and 0 <= rank_index < 8:
        result |= 1 << (rank_index * 8 + file_index)
        file_index += file_delta
        rank_index += rank_delta
    return result


RAYS: Final[tuple[tuple[Bitboard, ...], ...]] = tuple(
    tuple(_build_ray(Square(square), *DIRECTION_DELTAS[direction]) for square in range(64))
    for direction in range(8)
)

_KNIGHT_DELTAS: Final = (
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
)


def _build_knight(square: Square) -> Bitboard:
    result = 0
    file_index = file_of(square)
    rank_index = rank_of(square)
    for file_delta, rank_delta in _KNIGHT_DELTAS:
        new_file = file_index + file_delta
        new_rank = rank_index + rank_delta
        if 0 <= new_file < 8 and 0 <= new_rank < 8:
            result |= 1 << (new_rank * 8 + new_file)
    return result


def _build_king(square: Square) -> Bitboard:
    result = 0
    file_index = file_of(square)
    rank_index = rank_of(square)
    for file_delta, rank_delta in DIRECTION_DELTAS:
        new_file = file_index + file_delta
        new_rank = rank_index + rank_delta
        if 0 <= new_file < 8 and 0 <= new_rank < 8:
            result |= 1 << (new_rank * 8 + new_file)
    return result


KNIGHT_ATTACKS: Final = tuple(_build_knight(Square(square)) for square in range(64))
KING_ATTACKS: Final = tuple(_build_king(Square(square)) for square in range(64))


def _build_between(a: Square, b: Square) -> Bitboard:
    if a == b:
        return 0
    delta_file = file_of(b) - file_of(a)
    delta_rank = rank_of(b) - rank_of(a)
    if delta_file and delta_rank and abs(delta_file) != abs(delta_rank):
        return 0
    step_file = (delta_file > 0) - (delta_file < 0)
    step_rank = (delta_rank > 0) - (delta_rank < 0)
    result = 0
    file_index = file_of(a) + step_file
    rank_index = rank_of(a) + step_rank
    while (file_index, rank_index) != (file_of(b), rank_of(b)):
        result |= 1 << (rank_index * 8 + file_index)
        file_index += step_file
        rank_index += step_rank
    return result


BETWEEN: Final = tuple(
    tuple(_build_between(Square(a), Square(b)) for b in range(64)) for a in range(64)
)


def _build_line(a: Square, b: Square) -> Bitboard:
    if a == b:
        return square_bb(a)
    delta_file = file_of(b) - file_of(a)
    delta_rank = rank_of(b) - rank_of(a)
    if delta_file and delta_rank and abs(delta_file) != abs(delta_rank):
        return 0
    if delta_file == 0:
        directions = (NORTH, SOUTH)
    elif delta_rank == 0:
        directions = (EAST, WEST)
    elif delta_file * delta_rank > 0:
        directions = (NORTH_EAST, SOUTH_WEST)
    else:
        directions = (NORTH_WEST, SOUTH_EAST)
    result = square_bb(a) | square_bb(b)
    for direction in directions:
        result |= RAYS[direction][a]
    return result


LINE: Final = tuple(tuple(_build_line(Square(a), Square(b)) for b in range(64)) for a in range(64))
