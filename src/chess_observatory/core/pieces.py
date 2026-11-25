"""Piece and colour encoding (plan Phase 1, step 2).

A piece is a small integer that fits in the 64-byte mailbox:

===========  =====
value        piece
===========  =====
0            empty
1 … 6        white pawn, knight, bishop, rook, queen, king
9 … 14       black pawn, knight, bishop, rook, queen, king
===========  =====

Bit 3 is the colour bit, so ``piece & 7`` is the piece type and
``piece & 8`` is black. White is ``0`` and black is ``1`` in :class:`Color`.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final, NewType

Piece = NewType("Piece", int)

NO_PIECE: Final = Piece(0)
BLACK_BIT: Final = 8


class Color(IntEnum):
    WHITE = 0
    BLACK = 1

    @property
    def opposite(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def sign(self) -> int:
        """``+1`` for white, ``-1`` for black (used by evaluation terms)."""
        return 1 if self is Color.WHITE else -1

    @property
    def name(self) -> str:
        return "white" if self is Color.WHITE else "black"


class PieceType(IntEnum):
    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6

    @property
    def letter(self) -> str:
        return "PNBRQK"[self.value - 1]

    @property
    def name(self) -> str:
        return ("pawn", "knight", "bishop", "rook", "queen", "king")[self.value - 1]


WHITE_PAWN: Final = Piece(1)
WHITE_KNIGHT: Final = Piece(2)
WHITE_BISHOP: Final = Piece(3)
WHITE_ROOK: Final = Piece(4)
WHITE_QUEEN: Final = Piece(5)
WHITE_KING: Final = Piece(6)
BLACK_PAWN: Final = Piece(9)
BLACK_KNIGHT: Final = Piece(10)
BLACK_BISHOP: Final = Piece(11)
BLACK_ROOK: Final = Piece(12)
BLACK_QUEEN: Final = Piece(13)
BLACK_KING: Final = Piece(14)

PIECES: Final = (
    WHITE_PAWN,
    WHITE_KNIGHT,
    WHITE_BISHOP,
    WHITE_ROOK,
    WHITE_QUEEN,
    WHITE_KING,
    BLACK_PAWN,
    BLACK_KNIGHT,
    BLACK_BISHOP,
    BLACK_ROOK,
    BLACK_QUEEN,
    BLACK_KING,
)

PIECE_TO_CHAR: Final[dict[int, str]] = {
    WHITE_PAWN: "P",
    WHITE_KNIGHT: "N",
    WHITE_BISHOP: "B",
    WHITE_ROOK: "R",
    WHITE_QUEEN: "Q",
    WHITE_KING: "K",
    BLACK_PAWN: "p",
    BLACK_KNIGHT: "n",
    BLACK_BISHOP: "b",
    BLACK_ROOK: "r",
    BLACK_QUEEN: "q",
    BLACK_KING: "k",
}
CHAR_TO_PIECE: Final[dict[str, Piece]] = {
    char: Piece(value) for value, char in PIECE_TO_CHAR.items()
}

PIECE_TO_SYMBOL: Final[dict[int, str]] = {
    WHITE_PAWN: "♙",
    WHITE_KNIGHT: "♘",
    WHITE_BISHOP: "♗",
    WHITE_ROOK: "♖",
    WHITE_QUEEN: "♕",
    WHITE_KING: "♔",
    BLACK_PAWN: "♟",
    BLACK_KNIGHT: "♞",
    BLACK_BISHOP: "♝",
    BLACK_ROOK: "♜",
    BLACK_QUEEN: "♛",
    BLACK_KING: "♚",
}

SLIDING_TYPES: Final = frozenset({PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN})
ORTHOGONAL_TYPES: Final = frozenset({PieceType.ROOK, PieceType.QUEEN})
DIAGONAL_TYPES: Final = frozenset({PieceType.BISHOP, PieceType.QUEEN})


def make_piece(color: Color, piece_type: PieceType) -> Piece:
    return Piece(int(piece_type) | (BLACK_BIT if color is Color.BLACK else 0))


def color_of(piece: Piece) -> Color:
    if piece == NO_PIECE:
        raise ValueError("the empty square has no colour")
    return Color.BLACK if int(piece) & BLACK_BIT else Color.WHITE


def type_of(piece: Piece) -> PieceType:
    if piece == NO_PIECE:
        raise ValueError("the empty square has no piece type")
    return PieceType(int(piece) & 7)


def piece_from_char(char: str) -> Piece:
    try:
        return CHAR_TO_PIECE[char]
    except KeyError as exc:
        raise ValueError(f"not a piece character: {char!r}") from exc


def piece_to_char(piece: Piece) -> str:
    if piece == NO_PIECE:
        return "."
    return PIECE_TO_CHAR[int(piece)]


def piece_index(color: Color, piece_type: PieceType) -> int:
    """Index into a 12-element per-piece bitboard tuple."""
    return int(color) * 6 + int(piece_type) - 1


def index_color(index: int) -> Color:
    return Color(index // 6)


def index_type(index: int) -> PieceType:
    return PieceType(index % 6 + 1)


def index_piece(index: int) -> Piece:
    return make_piece(index_color(index), index_type(index))
