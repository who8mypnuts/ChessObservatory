"""Packed moves and the move list (plan Phase 1, step 3).

A move is a 32-bit integer laid out as::

    bits  0-5   from square
    bits  6-11  to square
    bits 12-15  promotion piece type (0 when none)
    bits 16-20  flags

The layout is deliberately small so a move list is an ``array('i')`` and
comparisons are integer comparisons. Flags are metadata for make/unmake and
the UI; two moves are the same move when from, to and promotion match.
"""

from __future__ import annotations

from array import array
from enum import IntFlag
from typing import Final, NewType, cast

from chess_observatory.core.pieces import PieceType
from chess_observatory.core.squares import Square, parse_square, square_name

Move = NewType("Move", int)

MOVE_NONE: Final = Move(0)
FROM_MASK: Final = 0x3F
TO_MASK: Final = 0x3F
PROMO_MASK: Final = 0xF
FLAGS_MASK: Final = 0x1F
FROM_SHIFT: Final = 0
TO_SHIFT: Final = 6
PROMO_SHIFT: Final = 12
FLAGS_SHIFT: Final = 16
IDENTITY_MASK: Final = (1 << 16) - 1


class MoveFlags(IntFlag):
    NONE = 0
    CAPTURE = 1 << 0
    EN_PASSANT = 1 << 1
    CASTLE = 1 << 2
    DOUBLE_PUSH = 1 << 3
    PROMOTION = 1 << 4


class MoveList(array[int]):
    """``array('i')`` of packed moves.

    A class rather than a bare alias so the type is nameable and the typecode
    cannot be forgotten. It is deliberately not a list: perft allocates one per
    node and the array is smaller and faster to clear.
    """

    def __new__(cls) -> MoveList:
        return cast("MoveList", super().__new__(cls, "i"))


def pack_move(
    from_square: Square,
    to_square: Square,
    promotion: PieceType | int = 0,
    flags: MoveFlags | int = MoveFlags.NONE,
) -> Move:
    value = (
        (int(from_square) & FROM_MASK)
        | ((int(to_square) & TO_MASK) << TO_SHIFT)
        | ((int(promotion) & PROMO_MASK) << PROMO_SHIFT)
        | ((int(flags) & FLAGS_MASK) << FLAGS_SHIFT)
    )
    return Move(value)


def move_from(move: int) -> Square:
    return Square((int(move) >> FROM_SHIFT) & FROM_MASK)


def move_to(move: int) -> Square:
    return Square((int(move) >> TO_SHIFT) & TO_MASK)


def move_promotion(move: int) -> PieceType | None:
    value = (int(move) >> PROMO_SHIFT) & PROMO_MASK
    return PieceType(value) if value else None


def move_flags(move: int) -> MoveFlags:
    return MoveFlags((int(move) >> FLAGS_SHIFT) & FLAGS_MASK)


def move_is_capture(move: int) -> bool:
    return bool(move_flags(move) & MoveFlags.CAPTURE)


def move_is_en_passant(move: int) -> bool:
    return bool(move_flags(move) & MoveFlags.EN_PASSANT)


def move_is_castle(move: int) -> bool:
    return bool(move_flags(move) & MoveFlags.CASTLE)


def move_is_double_push(move: int) -> bool:
    return bool(move_flags(move) & MoveFlags.DOUBLE_PUSH)


def move_is_promotion(move: int) -> bool:
    return move_promotion(move) is not None


def same_move(a: int, b: int) -> bool:
    """Compare identity, ignoring metadata flags."""
    return (int(a) & IDENTITY_MASK) == (int(b) & IDENTITY_MASK)


def move_to_uci(move: int) -> str:
    if move == MOVE_NONE:
        return "0000"
    text = f"{square_name(move_from(move))}{square_name(move_to(move))}"
    promotion = move_promotion(move)
    if promotion is not None:
        text += promotion.letter.lower()
    return text


def move_from_uci(text: str) -> Move:
    """Parse ``e2e4`` or ``e7e8q``. Flags are added by move generation."""
    cleaned = text.strip().lower()
    if cleaned in {"0000", "-", ""}:
        return MOVE_NONE
    if len(cleaned) not in {4, 5}:
        raise ValueError(f"not a UCI move: {text!r}")
    from_square = parse_square(cleaned[:2])
    to_square = parse_square(cleaned[2:4])
    promotion: PieceType | int = 0
    if len(cleaned) == 5:
        letter = cleaned[4]
        if letter not in "nbrq":
            raise ValueError(f"not a promotion piece: {letter!r}")
        promotion = PieceType("nbrq".index(letter) + 2)
    return pack_move(from_square, to_square, promotion)


def move_to_str(move: int) -> str:
    """Readable form for logs and test failures."""
    flags = move_flags(move)
    return f"{move_to_uci(move)} [{flags.name}]" if flags else move_to_uci(move)
