"""Immutable position snapshot (plan Phase 1, step 4).

``Position`` is a frozen value: two positions with the same fields are equal and
safe to cache. Mutation lives in :mod:`chess_observatory.core.make`, which owns
the undo stack and updates bitboards incrementally.

The 12 piece bitboards are indexed by :func:`chess_observatory.core.pieces.piece_index`:
``0..5`` white pawn..king, ``6..11`` black pawn..king.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final, Protocol

from chess_observatory.core.pieces import (
    NO_PIECE,
    PIECE_TO_CHAR,
    Color,
    Piece,
    PieceType,
    color_of,
    index_piece,
    piece_index,
    type_of,
)
from chess_observatory.core.squares import (
    FULL_BB,
    Square,
    lsb,
    square_bb,
)

CASTLE_WHITE_KING: Final = 1
CASTLE_WHITE_QUEEN: Final = 2
CASTLE_BLACK_KING: Final = 4
CASTLE_BLACK_QUEEN: Final = 8
CASTLE_ALL: Final = CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN | CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN

CASTLING_SQUARES: Final[dict[int, tuple[Square, ...]]] = {
    CASTLE_WHITE_KING: (Square(4), Square(5), Square(6), Square(7)),
    CASTLE_WHITE_QUEEN: (Square(4), Square(3), Square(2), Square(1), Square(0)),
    CASTLE_BLACK_KING: (Square(60), Square(61), Square(62), Square(63)),
    CASTLE_BLACK_QUEEN: (Square(60), Square(59), Square(58), Square(57), Square(56)),
}

ROOK_FROM_CASTLING: Final[dict[int, Square]] = {
    CASTLE_WHITE_KING: Square(7),
    CASTLE_WHITE_QUEEN: Square(0),
    CASTLE_BLACK_KING: Square(63),
    CASTLE_BLACK_QUEEN: Square(56),
}


@dataclass(frozen=True, slots=True)
class Position:
    """A complete chess position, including experimental (non-strict) states."""

    bb: tuple[int, ...]
    mailbox: bytes
    side: Color
    castling: int
    ep: Square | None
    halfmove: int
    fullmove: int
    strict: bool = True
    variant_note: str | None = None

    def __post_init__(self) -> None:
        if len(self.bb) != 12:
            raise ValueError(f"expected 12 piece bitboards, got {len(self.bb)}")
        if len(self.mailbox) != 64:
            raise ValueError(f"expected a 64-byte mailbox, got {len(self.mailbox)}")
        if not isinstance(self.side, Color):
            raise ValueError(f"side must be a Color, got {self.side!r}")
        if self.castling & ~CASTLE_ALL:
            raise ValueError(f"invalid castling mask: {self.castling}")
        if self.ep is not None and not 0 <= int(self.ep) < 64:
            raise ValueError(f"invalid en-passant square: {self.ep!r}")
        if self.halfmove < 0 or self.fullmove < 0:
            raise ValueError("clocks cannot be negative")
        occupied = 0
        for board in self.bb:
            if board & ~FULL_BB:
                raise ValueError("bitboard has bits outside the board")
            if board & occupied:
                raise ValueError("piece bitboards overlap")
            occupied |= board

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def empty(cls, side: Color = Color.WHITE) -> Position:
        return cls(
            bb=(0,) * 12,
            mailbox=bytes(64),
            side=side,
            castling=0,
            ep=None,
            halfmove=0,
            fullmove=1,
        )

    @classmethod
    def from_pieces(
        cls,
        pieces: Mapping[Square, Piece],
        *,
        side: Color = Color.WHITE,
        castling: int = 0,
        ep: Square | None = None,
        halfmove: int = 0,
        fullmove: int = 1,
        strict: bool = True,
        variant_note: str | None = None,
    ) -> Position:
        boards = [0] * 12
        mailbox = bytearray(64)
        for square, piece in pieces.items():
            if piece == NO_PIECE:
                continue
            boards[piece_index(color_of(piece), type_of(piece))] |= square_bb(square)
            mailbox[int(square)] = int(piece)
        return cls(
            bb=tuple(boards),
            mailbox=bytes(mailbox),
            side=side,
            castling=castling,
            ep=ep,
            halfmove=halfmove,
            fullmove=fullmove,
            strict=strict,
            variant_note=variant_note,
        )

    # ------------------------------------------------------------------ #
    # Board queries
    # ------------------------------------------------------------------ #
    def piece_at(self, square: Square) -> Piece:
        return Piece(self.mailbox[int(square)])

    def is_empty(self, square: Square) -> bool:
        return self.mailbox[int(square)] == 0

    def has_piece(self, square: Square) -> bool:
        return self.mailbox[int(square)] != 0

    def pieces(self, color: Color, piece_type: PieceType) -> int:
        return self.bb[piece_index(color, piece_type)]

    def color_occupancy(self, color: Color) -> int:
        base = 0 if color is Color.WHITE else 6
        return (
            self.bb[base]
            | self.bb[base + 1]
            | self.bb[base + 2]
            | self.bb[base + 3]
            | self.bb[base + 4]
            | self.bb[base + 5]
        )

    @property
    def occupancy(self) -> int:
        return self.color_occupancy(Color.WHITE) | self.color_occupancy(Color.BLACK)

    @property
    def occupied(self) -> int:
        return self.occupancy

    def king_square(self, color: Color) -> Square | None:
        board = self.pieces(color, PieceType.KING)
        return lsb(board) if board else None

    def piece_map(self) -> dict[Square, Piece]:
        return {Square(square): Piece(value) for square, value in enumerate(self.mailbox) if value}

    def piece_list(self, color: Color) -> list[tuple[Square, Piece]]:
        return [
            (Square(square), Piece(value))
            for square, value in enumerate(self.mailbox)
            if value and color_of(Piece(value)) is color
        ]

    def can_castle(self, color: Color, kingside: bool) -> bool:
        bit = CASTLE_WHITE_KING if color is Color.WHITE else CASTLE_BLACK_KING
        if not kingside:
            bit <<= 1
        return bool(self.castling & bit)

    # ------------------------------------------------------------------ #
    # Value semantics
    # ------------------------------------------------------------------ #
    def copy(self, **changes: Any) -> Position:
        """Return a modified copy; the original is untouched."""
        return replace(self, **changes)

    def is_consistent(self) -> bool:
        """Full mailbox/bitboard agreement. Used by debug assertions and tests."""
        boards = [0] * 12
        for square, value in enumerate(self.mailbox):
            if not value:
                continue
            if value & ~0x0F or (value & 7) == 0 or (value & 7) > 6:
                return False
            color = color_of(Piece(value))
            boards[piece_index(color, PieceType(value & 7))] |= 1 << square
        return tuple(boards) == self.bb

    def __str__(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = []
            for file_index in range(8):
                value = self.mailbox[rank * 8 + file_index]
                row.append(_piece_letter(value))
            rows.append(f"{rank + 1} " + " ".join(row))
        rows.append("  a b c d e f g h")
        return "\n".join(rows)


def _piece_letter(value: int) -> str:
    if not value:
        return "."
    return PIECE_TO_CHAR[value]


def piece_at_index(index: int) -> Piece:
    return index_piece(index)


class BoardView(Protocol):
    """Read-only surface shared by :class:`Position` and the mutable ``Board``.

    Move generation and attack code accept either: the immutable snapshot for
    analysis, the mutable board for perft and search.
    """

    @property
    def bb(self) -> Sequence[int]: ...

    @property
    def mailbox(self) -> Sequence[int]: ...

    @property
    def side(self) -> Color: ...

    @property
    def castling(self) -> int: ...

    @property
    def ep(self) -> Square | None: ...

    @property
    def halfmove(self) -> int: ...

    @property
    def fullmove(self) -> int: ...

    @property
    def strict(self) -> bool: ...

    @property
    def variant_note(self) -> str | None: ...

    @property
    def occupancy(self) -> int: ...

    def piece_at(self, square: Square) -> Piece: ...

    def pieces(self, color: Color, piece_type: PieceType) -> int: ...

    def color_occupancy(self, color: Color) -> int: ...

    def king_square(self, color: Color) -> Square | None: ...
