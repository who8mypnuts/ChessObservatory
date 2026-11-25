"""Standard Algebraic Notation: generation and parsing (plan Phase 1, step 11).

Generation is canonical: ``O-O`` uses letter O, captures carry ``x``, pawn
captures carry their origin file, disambiguation is the minimal legal one, and a
promotion is written ``=Q``. Parsing is deliberately tolerant of the variants
that appear in real PGN files: ``0-0`` for castling, a missing ``=`` before a
promotion piece, ``++`` or ``#`` for check, and a missing capture marker when the
move is otherwise unambiguous.

Both directions resolve through :func:`~chess_observatory.core.movegen.generate_legal`,
so a parsed SAN move always comes back with the flags that make/unmake needs.
"""

from __future__ import annotations

import re

from chess_observatory.core.attacks import in_check
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import (
    find_legal,
    generate_legal,
    is_checkmate,
)
from chess_observatory.core.moves import (
    MoveFlags,
    move_flags,
    move_from,
    move_promotion,
    move_to,
)
from chess_observatory.core.pieces import PieceType, type_of
from chess_observatory.core.position import BoardView
from chess_observatory.core.squares import (
    file_of,
    parse_square,
    rank_of,
    square_name,
)
from chess_observatory.errors import IllegalMoveError, InvalidSanError

PIECE_LETTERS = "KQRBN"
PIECE_TYPES: dict[str, PieceType] = {
    "K": PieceType.KING,
    "Q": PieceType.QUEEN,
    "R": PieceType.ROOK,
    "B": PieceType.BISHOP,
    "N": PieceType.KNIGHT,
}
_CASTLE_KINGSIDE = frozenset({"O-O", "0-0"})
_CASTLE_QUEENSIDE = frozenset({"O-O-O", "0-0-0"})
_ANNOTATION = re.compile(r"[!?]+$")


def to_san(position: BoardView, move: int) -> str:
    """Render a legal move in canonical SAN, including check/mate markers."""
    resolved = find_legal(position, move)
    if resolved is None:
        raise IllegalMoveError(
            f"illegal move {move:#x} in {position!r}",
            context={"move": move},
        )
    move = resolved
    origin = move_from(move)
    target = move_to(move)
    piece = position.piece_at(origin)
    piece_type = type_of(piece)
    flags = move_flags(move)
    is_capture = bool(flags & MoveFlags.CAPTURE)

    if flags & MoveFlags.CASTLE:
        text = "O-O" if file_of(target) > file_of(origin) else "O-O-O"
    elif piece_type is PieceType.PAWN:
        text = ""
        if is_capture:
            text += "abcdefgh"[file_of(origin)] + "x"
        text += square_name(target)
        promotion = move_promotion(move)
        if promotion is not None:
            text += "=" + promotion.letter
    else:
        text = piece_type.letter
        text += _disambiguation(position, move, piece_type)
        if is_capture:
            text += "x"
        text += square_name(target)

    board = Board.from_position(position)
    board.make(move)
    if is_checkmate(board):
        text += "#"
    elif in_check(board, board.side):
        text += "+"
    return text


def _disambiguation(position: BoardView, move: int, piece_type: PieceType) -> str:
    origin = move_from(move)
    target = move_to(move)
    candidates = [
        candidate
        for candidate in generate_legal(position)
        if move_to(candidate) == target
        and type_of(position.piece_at(move_from(candidate))) is piece_type
        and move_promotion(candidate) == move_promotion(move)
    ]
    if len(candidates) <= 1:
        return ""
    same_file = [item for item in candidates if file_of(move_from(item)) == file_of(origin)]
    if len(same_file) == 1:
        return "abcdefgh"[file_of(origin)]
    same_rank = [item for item in candidates if rank_of(move_from(item)) == rank_of(origin)]
    if len(same_rank) == 1:
        return "12345678"[rank_of(origin)]
    return "abcdefgh"[file_of(origin)] + "12345678"[rank_of(origin)]


def parse_san(position: BoardView, text: str) -> int:
    """Resolve SAN text to the unique legal move, flags included."""
    original = text
    body = text.strip()
    if not body:
        raise InvalidSanError("empty SAN move", context={"san": original})

    if body.endswith("e.p."):
        body = body[:-4].rstrip()
    body = _ANNOTATION.sub("", body)
    while body.endswith(("+", "#")):
        body = body[:-1]
    body = _ANNOTATION.sub("", body).strip()
    if not body:
        raise InvalidSanError(f"no move in SAN text {original!r}", context={"san": original})

    if body in _CASTLE_KINGSIDE or body in _CASTLE_QUEENSIDE:
        return _parse_castle(position, original, kingside=body in _CASTLE_KINGSIDE)

    promotion: PieceType | None = None
    if "=" in body:
        body, _, letter = body.partition("=")
        promotion = _promotion_piece(letter, original)
    elif len(body) >= 3 and body[-1].upper() in PIECE_LETTERS and body[-2].isdigit():
        promotion = _promotion_piece(body[-1], original)
        body = body[:-1]

    capture_marker = "x" in body or "X" in body
    body = body.replace("x", "").replace("X", "")
    if len(body) < 2:
        raise InvalidSanError(f"cannot parse SAN move {original!r}", context={"san": original})

    destination_text = body[-2:]
    prefix = body[:-2]
    try:
        destination = parse_square(destination_text)
    except ValueError as exc:
        raise InvalidSanError(
            f"invalid destination in SAN move {original!r}",
            context={"san": original},
        ) from exc

    piece_type = PieceType.PAWN
    file_hint: int | None = None
    rank_hint: int | None = None
    if prefix and prefix[0] in PIECE_LETTERS:
        piece_type = PIECE_TYPES[prefix[0]]
        prefix = prefix[1:]
    if len(prefix) > 2:
        raise InvalidSanError(f"cannot parse SAN move {original!r}", context={"san": original})
    for char in prefix:
        if char in "abcdefgh":
            if file_hint is not None:
                raise InvalidSanError(
                    f"duplicate file in SAN move {original!r}", context={"san": original}
                )
            file_hint = "abcdefgh".index(char)
        elif char in "12345678":
            if rank_hint is not None:
                raise InvalidSanError(
                    f"duplicate rank in SAN move {original!r}", context={"san": original}
                )
            rank_hint = "12345678".index(char)
        else:
            raise InvalidSanError(
                f"invalid disambiguation in SAN move {original!r}", context={"san": original}
            )

    def matches(move: int, *, require_capture: bool | None) -> bool:
        if move_to(move) != destination:
            return False
        if type_of(position.piece_at(move_from(move))) is not piece_type:
            return False
        if promotion is not None and move_promotion(move) is not promotion:
            return False
        if promotion is None and move_promotion(move) is not None:
            return False
        if file_hint is not None and file_of(move_from(move)) != file_hint:
            return False
        if rank_hint is not None and rank_of(move_from(move)) != rank_hint:
            return False
        capture = bool(move_flags(move) & MoveFlags.CAPTURE)
        return require_capture is None or capture == require_capture

    legal = generate_legal(position)
    if capture_marker:
        candidates = [move for move in legal if matches(move, require_capture=True)]
    else:
        candidates = [move for move in legal if matches(move, require_capture=False)]
        if not candidates:
            # Tolerate PGNs that omit the capture marker.
            candidates = [move for move in legal if matches(move, require_capture=None)]
    if not candidates:
        raise InvalidSanError(
            f"illegal or unparseable SAN move {original!r}",
            context={"san": original, "side": position.side.name},
        )
    if len(candidates) > 1:
        raise InvalidSanError(
            f"ambiguous SAN move {original!r}",
            context={"san": original, "candidates": len(candidates)},
        )
    return candidates[0]


def _parse_castle(position: BoardView, original: str, *, kingside: bool) -> int:
    for move in generate_legal(position):
        if not move_flags(move) & MoveFlags.CASTLE:
            continue
        if (file_of(move_to(move)) > file_of(move_from(move))) == kingside:
            return move
    raise InvalidSanError(
        f"castling is not legal here: {original!r}",
        context={"san": original},
    )


def _promotion_piece(letter: str, original: str) -> PieceType:
    cleaned = letter.strip().upper()
    if cleaned == "K" or cleaned == "P" or cleaned not in PIECE_LETTERS:
        raise InvalidSanError(
            f"invalid promotion piece in SAN move {original!r}",
            context={"san": original},
        )
    return PIECE_TYPES[cleaned]


def san_roundtrip(position: BoardView, move: int) -> int:
    """Convenience for tests and importers: render then parse the same move."""
    return parse_san(position, to_san(position, move))
