"""Counterfactual position edits (plan Phase 1, step 9).

The instrument must be able to ask "what if this piece were not here?" without
pretending the answer is a legal chess position. Every edit returns the new
:class:`~chess_observatory.core.position.Position` together with a
:class:`LegalityReport` that names every rule the result violates. A position
with violations is stored with ``strict=False`` and a ``variant_note`` built from
the report, so later analyses can label themselves honestly.

Edits never raise for an illegal *result*; they raise only when the edit itself
is impossible (adding to an occupied square without ``replace=True``, relocating
from an empty square, or setting a castling mask outside the defined bits).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from chess_observatory.core.attacks import in_check
from chess_observatory.core.pieces import (
    BLACK_KING,
    BLACK_ROOK,
    WHITE_KING,
    WHITE_ROOK,
    Color,
    Piece,
    PieceType,
    color_of,
)
from chess_observatory.core.position import (
    CASTLE_ALL,
    CASTLE_BLACK_KING,
    CASTLE_BLACK_QUEEN,
    CASTLE_WHITE_KING,
    CASTLE_WHITE_QUEEN,
    Position,
)
from chess_observatory.core.squares import (
    RANK_1,
    RANK_8,
    Square,
    file_of,
    parse_square,
    rank_of,
    square_distance,
    square_name,
)
from chess_observatory.errors import InvalidPositionError

_CASTLING_RIGHTS: Final = (
    (CASTLE_WHITE_KING, Color.WHITE, True),
    (CASTLE_WHITE_QUEEN, Color.WHITE, False),
    (CASTLE_BLACK_KING, Color.BLACK, True),
    (CASTLE_BLACK_QUEEN, Color.BLACK, False),
)


class Relaxation(StrEnum):
    """A rule that an edited position no longer satisfies."""

    MISSING_KING = "missing_king"
    MULTIPLE_KINGS = "multiple_kings"
    ADJACENT_KINGS = "adjacent_kings"
    PAWN_ON_BACK_RANK = "pawn_on_back_rank"
    TOO_MANY_PAWNS = "too_many_pawns"
    TOO_MANY_PIECES = "too_many_pieces"
    CASTLING_WITHOUT_KING = "castling_without_king"
    CASTLING_WITHOUT_ROOK = "castling_without_rook"
    EN_PASSANT_ON_WRONG_RANK = "en_passant_on_wrong_rank"
    EN_PASSANT_WITHOUT_PAWN = "en_passant_without_pawn"
    EN_PASSANT_WITHOUT_CLOCK = "en_passant_without_clock"
    SIDE_NOT_TO_MOVE_IN_CHECK = "side_not_to_move_in_check"


@dataclass(frozen=True, slots=True)
class LegalityReport:
    """What remains of the rules after an edit."""

    legal: bool
    relaxed: frozenset[Relaxation]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "legal": self.legal,
            "relaxed": sorted(item.value for item in self.relaxed),
            "notes": list(self.notes),
        }

    def describe(self) -> str:
        if self.legal:
            return "legal position"
        return "; ".join(self.notes)


LEGAL_REPORT: Final = LegalityReport(legal=True, relaxed=frozenset(), notes=())


def inspect_position(position: Position) -> LegalityReport:
    """Check every rule that a legal chess position must satisfy."""
    relaxed: set[Relaxation] = set()
    notes: list[str] = []

    def fail(rule: Relaxation, note: str) -> None:
        relaxed.add(rule)
        notes.append(note)

    for color in Color:
        king = position.king_square(color)
        if king is None:
            fail(Relaxation.MISSING_KING, f"no {color.name} king")
        elif position.pieces(color, PieceType.KING).bit_count() > 1:
            fail(Relaxation.MULTIPLE_KINGS, f"more than one {color.name} king")

        pawns = position.pieces(color, PieceType.PAWN)
        if pawns & (RANK_1 | RANK_8):
            fail(Relaxation.PAWN_ON_BACK_RANK, f"{color.name} pawn on the first or eighth rank")
        if pawns.bit_count() > 8:
            fail(Relaxation.TOO_MANY_PAWNS, f"{color.name} has more than eight pawns")
        if position.color_occupancy(color).bit_count() > 16:
            fail(Relaxation.TOO_MANY_PIECES, f"{color.name} has more than sixteen pieces")

    white_king = position.king_square(Color.WHITE)
    black_king = position.king_square(Color.BLACK)
    if (
        white_king is not None
        and black_king is not None
        and square_distance(white_king, black_king) <= 1
    ):
        fail(Relaxation.ADJACENT_KINGS, "the two kings are adjacent")

    for mask, color, kingside in _CASTLING_RIGHTS:
        if not position.castling & mask:
            continue
        home = parse_square("e1") if color is Color.WHITE else parse_square("e8")
        rook_square = (
            parse_square("h1" if kingside else "a1")
            if color is Color.WHITE
            else parse_square("h8" if kingside else "a8")
        )
        expected_rook = WHITE_ROOK if color is Color.WHITE else BLACK_ROOK
        if position.king_square(color) != home:
            fail(
                Relaxation.CASTLING_WITHOUT_KING,
                f"{color.name} has castling rights but the king is not on {square_name(home)}",
            )
        if position.piece_at(rook_square) != expected_rook:
            fail(
                Relaxation.CASTLING_WITHOUT_ROOK,
                f"{color.name} has castling rights without a rook on {square_name(rook_square)}",
            )

    if position.ep is not None:
        expected_rank = 5 if position.side is Color.WHITE else 2
        if rank_of(position.ep) != expected_rank:
            fail(
                Relaxation.EN_PASSANT_ON_WRONG_RANK,
                f"en-passant square {square_name(position.ep)} is on the wrong rank for the side to move",
            )
        else:
            pawn_rank = 4 if position.side is Color.WHITE else 3
            pawn_square = Square(pawn_rank * 8 + file_of(position.ep))
            expected_pawn = 9 if position.side is Color.WHITE else 1
            if int(position.piece_at(pawn_square)) != expected_pawn:
                fail(
                    Relaxation.EN_PASSANT_WITHOUT_PAWN,
                    f"no pawn could have double-pushed to {square_name(position.ep)}",
                )
        if position.halfmove != 0:
            fail(
                Relaxation.EN_PASSANT_WITHOUT_CLOCK,
                "an en-passant position must have a halfmove clock of 0",
            )

    if (
        white_king is not None
        and black_king is not None
        and in_check(position, position.side.opposite)
    ):
        fail(
            Relaxation.SIDE_NOT_TO_MOVE_IN_CHECK,
            "the side not to move is in check",
        )

    return LegalityReport(
        legal=not relaxed,
        relaxed=frozenset(relaxed),
        notes=tuple(notes),
    )


def _finalize(position: Position) -> tuple[Position, LegalityReport]:
    report = inspect_position(position)
    note = report.describe() if not report.legal else None
    return position.copy(strict=report.legal, variant_note=note), report


def _with_pieces(position: Position, pieces: dict[Square, Piece]) -> Position:
    return Position.from_pieces(
        pieces,
        side=position.side,
        castling=position.castling,
        ep=position.ep,
        halfmove=position.halfmove,
        fullmove=position.fullmove,
        strict=False,
        variant_note=position.variant_note,
    )


def set_piece(
    position: Position,
    square: Square,
    piece: Piece,
    *,
    replace: bool = True,
) -> tuple[Position, LegalityReport]:
    """Put ``piece`` on ``square``; ``piece == 0`` clears the square."""
    if not replace and position.piece_at(square) != 0:
        raise InvalidPositionError(
            f"square {square_name(square)} is already occupied",
            hint="Pass replace=True to overwrite it.",
        )
    pieces = position.piece_map()
    if piece == 0:
        pieces.pop(square, None)
    else:
        pieces[square] = piece
    return _finalize(_with_pieces(position, pieces))


def add_piece(
    position: Position,
    square: Square,
    piece: Piece,
    *,
    replace: bool = False,
) -> tuple[Position, LegalityReport]:
    """Add a piece to an empty square, or overwrite with ``replace=True``."""
    return set_piece(position, square, piece, replace=replace)


def remove_piece(position: Position, square: Square) -> tuple[Position, LegalityReport]:
    """Remove the piece on ``square``; removing an empty square is a no-op."""
    if position.piece_at(square) == 0:
        return _finalize(position)
    pieces = position.piece_map()
    del pieces[square]
    return _finalize(_with_pieces(position, pieces))


def relocate_piece(
    position: Position,
    origin: Square,
    target: Square,
) -> tuple[Position, LegalityReport]:
    """Move the piece on ``origin`` to ``target``, replacing anything there."""
    piece = position.piece_at(origin)
    if piece == 0:
        raise InvalidPositionError(
            f"no piece on {square_name(origin)}",
            hint="Relocate needs a piece to move.",
        )
    pieces = position.piece_map()
    del pieces[origin]
    pieces[target] = piece
    return _finalize(_with_pieces(position, pieces))


def set_side(position: Position, side: Color) -> tuple[Position, LegalityReport]:
    """Change the side to move."""
    return _finalize(position.copy(side=side, ep=None))


def clear_castling(position: Position) -> tuple[Position, LegalityReport]:
    """Remove every castling right."""
    return _finalize(position.copy(castling=0))


def set_castling(position: Position, mask: int) -> tuple[Position, LegalityReport]:
    """Set the castling mask; the report names any rights that do not fit."""
    if mask & ~CASTLE_ALL:
        raise InvalidPositionError(
            f"invalid castling mask {mask:#x}",
            hint="Use the CASTLE_* constants; the valid bits are K, Q, k, q.",
        )
    return _finalize(position.copy(castling=mask))


def set_ep(
    position: Position,
    square: Square | None,
) -> tuple[Position, LegalityReport]:
    """Set or clear the en-passant square."""
    return _finalize(position.copy(ep=square))


def null_move(position: Position) -> tuple[Position, LegalityReport]:
    """Pass the move: flip the side, clear en passant and advance the clocks."""
    fullmove = position.fullmove + (1 if position.side is Color.BLACK else 0)
    return _finalize(
        position.copy(
            side=position.side.opposite,
            ep=None,
            halfmove=position.halfmove + 1,
            fullmove=fullmove,
        )
    )


def swap_kings(position: Position) -> tuple[Position, LegalityReport]:
    """Exchange the two kings; useful for counterfactual king-safety studies."""
    white_king = position.king_square(Color.WHITE)
    black_king = position.king_square(Color.BLACK)
    if white_king is None or black_king is None:
        return _finalize(position)
    pieces = position.piece_map()
    pieces[white_king] = BLACK_KING
    pieces[black_king] = WHITE_KING
    return _finalize(_with_pieces(position, pieces))


def piece_belongs_to(piece: Piece, color: Color) -> bool:
    """Small helper shared by editor widgets and tests."""
    return piece != 0 and color_of(piece) is color
