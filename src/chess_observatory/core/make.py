"""Mutable board with incremental make/unmake (plan Phase 1, step 8).

``Position`` is the immutable public value. ``Board`` is the mutable worker used
by perft, search and move generation: it owns the undo stack and updates
bitboards, mailbox, Zobrist key, castling rights, clocks and en passant in place.

The undo record is a frozen dataclass with slots; every field that cannot be
derived from the move is stored. ``validate=True`` turns on full re-validation
after each make, which is how the test suite proves the incremental updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from chess_observatory.core.moves import (
    MoveFlags,
    move_flags,
    move_from,
    move_promotion,
    move_to,
)
from chess_observatory.core.pieces import (
    Color,
    Piece,
    PieceType,
    color_of,
    make_piece,
    piece_index,
    type_of,
)
from chess_observatory.core.position import (
    CASTLE_BLACK_KING,
    CASTLE_BLACK_QUEEN,
    CASTLE_WHITE_KING,
    CASTLE_WHITE_QUEEN,
    BoardView,
    Position,
)
from chess_observatory.core.squares import Square, file_of, square_bb
from chess_observatory.core.zobrist import (
    CASTLING_KEYS,
    EP_FILE_KEYS,
    PIECE_KEYS,
    SIDE_KEY,
    compute_key,
)
from chess_observatory.errors import IllegalMoveError

_ROOK_CASTLING_MASK: Final[dict[int, int]] = {
    0: CASTLE_WHITE_QUEEN,
    7: CASTLE_WHITE_KING,
    56: CASTLE_BLACK_QUEEN,
    63: CASTLE_BLACK_KING,
}

_KING_CASTLING_MASK: Final[dict[int, int]] = {
    4: CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN,
    60: CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN,
}

_CASTLE_ROOK: Final[dict[tuple[Color, bool], tuple[Square, Square]]] = {
    (Color.WHITE, True): (Square(7), Square(5)),
    (Color.WHITE, False): (Square(0), Square(3)),
    (Color.BLACK, True): (Square(63), Square(61)),
    (Color.BLACK, False): (Square(56), Square(59)),
}


@dataclass(frozen=True, slots=True)
class Undo:
    move: int
    captured: Piece
    captured_square: Square | None
    castling: int
    ep: Square | None
    halfmove: int
    fullmove: int
    key: int


class Board:
    """Mutable position with an undo stack."""

    __slots__ = (
        "_undo",
        "bb",
        "castling",
        "ep",
        "fullmove",
        "halfmove",
        "key",
        "mailbox",
        "side",
        "strict",
        "validate",
        "variant_note",
    )

    def __init__(self, position: BoardView, *, validate: bool = False) -> None:
        self.bb: list[int] = list(position.bb)
        self.mailbox = bytearray(position.mailbox)
        self.side = position.side
        self.castling = position.castling
        self.ep = position.ep
        self.halfmove = position.halfmove
        self.fullmove = position.fullmove
        self.key = compute_key(position)
        self.strict = position.strict
        self.variant_note = position.variant_note
        self.validate = validate
        self._undo: list[Undo] = []

    # ------------------------------------------------------------------ #
    # Snapshots
    # ------------------------------------------------------------------ #
    @classmethod
    def from_position(cls, position: BoardView, *, validate: bool = False) -> Board:
        return cls(position, validate=validate)

    def to_position(self) -> Position:
        return Position(
            bb=tuple(self.bb),
            mailbox=bytes(self.mailbox),
            side=self.side,
            castling=self.castling,
            ep=self.ep,
            halfmove=self.halfmove,
            fullmove=self.fullmove,
            strict=self.strict,
            variant_note=self.variant_note,
        )

    def copy(self) -> Board:
        clone = Board(self.to_position(), validate=self.validate)
        clone._undo = list(self._undo)
        return clone

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def piece_at(self, square: Square) -> Piece:
        return Piece(self.mailbox[int(square)])

    def is_empty(self, square: Square) -> bool:
        return self.mailbox[int(square)] == 0

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

    def king_square(self, color: Color) -> Square | None:
        board = self.pieces(color, PieceType.KING)
        if not board:
            return None
        return Square((board & -board).bit_length() - 1)

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    def is_consistent(self) -> bool:
        return self.to_position().is_consistent()

    # ------------------------------------------------------------------ #
    # Low-level piece updates (key included)
    # ------------------------------------------------------------------ #
    def _remove_piece(self, square: Square) -> Piece:
        piece = Piece(self.mailbox[int(square)])
        if piece == 0:
            raise IllegalMoveError(f"no piece on {square}")
        index = piece_index(color_of(piece), type_of(piece))
        self.bb[index] ^= square_bb(square)
        self.key ^= PIECE_KEYS[index][int(square)]
        self.mailbox[int(square)] = 0
        return piece

    def _add_piece(self, square: Square, piece: Piece) -> None:
        index = piece_index(color_of(piece), type_of(piece))
        self.bb[index] |= square_bb(square)
        self.key ^= PIECE_KEYS[index][int(square)]
        self.mailbox[int(square)] = int(piece)

    def _move_piece(self, origin: Square, target: Square) -> None:
        piece = self._remove_piece(origin)
        self._add_piece(target, piece)

    # ------------------------------------------------------------------ #
    # Make / unmake
    # ------------------------------------------------------------------ #
    def make(self, move: int) -> None:
        origin = move_from(move)
        target = move_to(move)
        flags = move_flags(move)
        piece = self.piece_at(origin)
        if piece == 0:
            raise IllegalMoveError(f"no piece on {origin}")

        captured_square: Square | None = target
        captured = self.piece_at(target)
        if flags & MoveFlags.EN_PASSANT:
            direction = 1 if color_of(piece) is Color.WHITE else -1
            captured_square = Square(int(target) - 8 * direction)
            captured = self.piece_at(captured_square)
        elif not captured:
            captured_square = None

        self._undo.append(
            Undo(
                move=move,
                captured=captured,
                captured_square=captured_square,
                castling=self.castling,
                ep=self.ep,
                halfmove=self.halfmove,
                fullmove=self.fullmove,
                key=self.key,
            )
        )

        self.key ^= SIDE_KEY
        if self.ep is not None:
            self.key ^= EP_FILE_KEYS[file_of(self.ep)]
        self.key ^= CASTLING_KEYS[self.castling]

        if captured != 0 and captured_square is not None:
            self._remove_piece(captured_square)

        promotion = move_promotion(move)
        if promotion is not None:
            self._remove_piece(origin)
            self._add_piece(target, make_piece(color_of(piece), promotion))
        else:
            self._move_piece(origin, target)

        if flags & MoveFlags.CASTLE:
            rook_from, rook_to = _CASTLE_ROOK[(color_of(piece), int(target) > int(origin))]
            self._move_piece(rook_from, rook_to)

        self.castling &= ~_KING_CASTLING_MASK.get(int(origin), 0)
        self.castling &= ~_ROOK_CASTLING_MASK.get(int(origin), 0)
        if captured_square is not None:
            self.castling &= ~_ROOK_CASTLING_MASK.get(int(captured_square), 0)

        if flags & MoveFlags.DOUBLE_PUSH:
            self.ep = Square((int(origin) + int(target)) // 2)
        else:
            self.ep = None

        if type_of(piece) is PieceType.PAWN or captured != 0:
            self.halfmove = 0
        else:
            self.halfmove += 1
        if self.side is Color.BLACK:
            self.fullmove += 1
        self.side = self.side.opposite

        self.key ^= CASTLING_KEYS[self.castling]
        if self.ep is not None:
            self.key ^= EP_FILE_KEYS[file_of(self.ep)]

        if self.validate:
            self._validate_after_make()

    def unmake(self) -> int:
        if not self._undo:
            raise IllegalMoveError("nothing to unmake")
        undo = self._undo.pop()
        move = undo.move
        origin = move_from(move)
        target = move_to(move)
        flags = move_flags(move)

        self.side = self.side.opposite
        promotion = move_promotion(move)
        if promotion is not None:
            self._remove_piece(target)
            self._add_piece(origin, make_piece(self.side, PieceType.PAWN))
        else:
            self._move_piece(target, origin)

        if flags & MoveFlags.CASTLE:
            rook_from, rook_to = _CASTLE_ROOK[(self.side, int(target) > int(origin))]
            self._move_piece(rook_to, rook_from)

        if undo.captured != 0 and undo.captured_square is not None:
            self._add_piece(undo.captured_square, undo.captured)

        self.castling = undo.castling
        self.ep = undo.ep
        self.halfmove = undo.halfmove
        self.fullmove = undo.fullmove
        self.key = undo.key
        if self.validate:
            self._validate_after_make()
        return move

    def _validate_after_make(self) -> None:
        if not self.is_consistent():
            raise AssertionError("board mailbox and bitboards disagree")
        expected = compute_key(self.to_position())
        if expected != self.key:
            raise AssertionError(f"incremental key {self.key:#x} != recomputed {expected:#x}")
