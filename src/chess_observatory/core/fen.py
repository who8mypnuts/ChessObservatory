"""FEN parsing and emission (plan Phase 1, step 10).

The strict parser rejects positions that could not arise from a legal game and
names the exact reason. The permissive parser keeps the same structural checks
(ranks, fields, characters) but accepts experimental states; the resulting
``Position`` carries ``strict=False`` and the edit/report layer explains what was
relaxed.

``to_fen`` is canonical: no trailing spaces, lower-case promotion pieces are not
relevant here, and the en-passant field is emitted whenever ``ep`` is set.
"""

from __future__ import annotations

from chess_observatory.core.attacks import in_check
from chess_observatory.core.movegen import has_legal_en_passant
from chess_observatory.core.pieces import (
    BLACK_ROOK,
    WHITE_ROOK,
    Color,
    Piece,
    PieceType,
    piece_from_char,
    piece_to_char,
)
from chess_observatory.core.position import (
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
from chess_observatory.errors import InvalidFenError

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_CASTLING_CHARS = (
    (CASTLE_WHITE_KING, "K"),
    (CASTLE_WHITE_QUEEN, "Q"),
    (CASTLE_BLACK_KING, "k"),
    (CASTLE_BLACK_QUEEN, "q"),
)


def parse_fen(text: str, *, strict: bool = True) -> Position:
    fields = text.strip().split()
    if len(fields) != 6:
        raise InvalidFenError(
            f"FEN has {len(fields)} field(s), expected 6.",
            context={"fen": text},
        )
    placement, side_field, castling_field, ep_field, halfmove_field, fullmove_field = fields

    pieces = _parse_placement(placement, text)
    side = _parse_side(side_field, text)
    castling = _parse_castling(castling_field, text)
    ep = _parse_ep(ep_field, text)
    halfmove = _parse_clock(halfmove_field, "halfmove", text)
    fullmove = _parse_clock(fullmove_field, "fullmove", text)

    position = Position.from_pieces(
        pieces,
        side=side,
        castling=castling,
        ep=ep,
        halfmove=halfmove,
        fullmove=fullmove,
        strict=strict,
    )
    if strict:
        _validate_strict(position)
    return position


def _parse_placement(placement: str, text: str) -> dict[Square, Piece]:
    ranks = placement.split("/")
    if len(ranks) != 8:
        raise InvalidFenError(
            f"FEN placement has {len(ranks)} rank(s), expected 8.",
            context={"fen": text, "placement": placement},
        )
    pieces: dict[Square, Piece] = {}
    for row, rank_text in enumerate(ranks):
        rank_index = 7 - row
        file_index = 0
        for char in rank_text:
            if char.isdigit():
                count = int(char)
                if count == 0:
                    raise InvalidFenError("FEN placement uses the digit 0.", context={"fen": text})
                file_index += count
                if file_index > 8:
                    raise InvalidFenError(
                        f"FEN rank {rank_index + 1} is wider than eight files.",
                        context={"fen": text, "rank": rank_index + 1},
                    )
            else:
                if file_index >= 8:
                    raise InvalidFenError(
                        f"FEN rank {rank_index + 1} is wider than eight files.",
                        context={"fen": text, "rank": rank_index + 1},
                    )
                try:
                    piece = piece_from_char(char)
                except ValueError as exc:
                    raise InvalidFenError(
                        f"Unknown piece character {char!r} in FEN.",
                        context={"fen": text, "character": char},
                    ) from exc
                pieces[Square(rank_index * 8 + file_index)] = piece
                file_index += 1
        if file_index != 8:
            raise InvalidFenError(
                f"FEN rank {rank_index + 1} has {file_index} file(s), expected 8.",
                context={"fen": text, "rank": rank_index + 1},
            )
    return pieces


def _parse_side(field: str, text: str) -> Color:
    if field == "w":
        return Color.WHITE
    if field == "b":
        return Color.BLACK
    raise InvalidFenError(
        f"Side-to-move must be 'w' or 'b', got {field!r}.",
        context={"fen": text, "side": field},
    )


def _parse_castling(field: str, text: str) -> int:
    if field == "-":
        return 0
    rights = 0
    seen: set[str] = set()
    for char in field:
        if char not in "KQkq":
            raise InvalidFenError(f"Invalid castling character {char!r}.", context={"fen": text})
        if char in seen:
            raise InvalidFenError(f"Duplicate castling character {char!r}.", context={"fen": text})
        seen.add(char)
        rights |= {char_value: mask for mask, char_value in _CASTLING_CHARS}[char]
    return rights


def _parse_ep(field: str, text: str) -> Square | None:
    if field == "-":
        return None
    try:
        square = parse_square(field)
    except ValueError as exc:
        raise InvalidFenError(
            f"Invalid en-passant square {field!r}.", context={"fen": text}
        ) from exc
    if rank_of(square) not in {2, 5}:
        raise InvalidFenError(
            "En-passant square must be on rank 3 or rank 6.",
            context={"fen": text, "square": field},
        )
    return square


def _parse_clock(field: str, name: str, text: str) -> int:
    try:
        value = int(field)
    except ValueError as exc:
        raise InvalidFenError(
            f"{name.capitalize()} clock is not an integer: {field!r}.",
            context={"fen": text},
        ) from exc
    if value < 0:
        raise InvalidFenError(
            f"{name.capitalize()} clock cannot be negative.", context={"fen": text}
        )
    return value


def _validate_strict(position: Position) -> None:
    for color in Color:
        king = position.king_square(color)
        if king is None:
            raise InvalidFenError(
                f"Position has no {color.name} king.",
                hint="Use strict=False for experimental positions.",
            )
        if position.pieces(color, PieceType.KING).bit_count() > 1:
            raise InvalidFenError(f"Position has more than one {color.name} king.")
        pawns = position.pieces(color, PieceType.PAWN)
        if pawns & (RANK_1 | RANK_8):
            raise InvalidFenError(
                f"{color.name.capitalize()} has a pawn on the first or eighth rank."
            )
        if pawns.bit_count() > 8:
            raise InvalidFenError(f"{color.name.capitalize()} has more than eight pawns.")
        if position.color_occupancy(color).bit_count() > 16:
            raise InvalidFenError(f"{color.name.capitalize()} has more than sixteen pieces.")
    white_king = position.king_square(Color.WHITE)
    black_king = position.king_square(Color.BLACK)
    assert white_king is not None and black_king is not None
    if square_distance(white_king, black_king) <= 1:
        raise InvalidFenError("The two kings are adjacent.")

    if position.castling & (CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN):
        if white_king != parse_square("e1"):
            raise InvalidFenError("White has castling rights but the king is not on e1.")
        if (
            position.castling & CASTLE_WHITE_KING
            and position.piece_at(parse_square("h1")) != WHITE_ROOK
        ):
            raise InvalidFenError("White has kingside castling rights without a rook on h1.")
        if (
            position.castling & CASTLE_WHITE_QUEEN
            and position.piece_at(parse_square("a1")) != WHITE_ROOK
        ):
            raise InvalidFenError("White has queenside castling rights without a rook on a1.")
    if position.castling & (CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN):
        if black_king != parse_square("e8"):
            raise InvalidFenError("Black has castling rights but the king is not on e8.")
        if (
            position.castling & CASTLE_BLACK_KING
            and position.piece_at(parse_square("h8")) != BLACK_ROOK
        ):
            raise InvalidFenError("Black has kingside castling rights without a rook on h8.")
        if (
            position.castling & CASTLE_BLACK_QUEEN
            and position.piece_at(parse_square("a8")) != BLACK_ROOK
        ):
            raise InvalidFenError("Black has queenside castling rights without a rook on a8.")

    if position.ep is not None:
        ep_rank = rank_of(position.ep)
        expected_rank = 5 if position.side is Color.WHITE else 2
        if ep_rank != expected_rank:
            raise InvalidFenError(
                "En-passant square is on the wrong rank for the side to move.",
                context={"ep": square_name(position.ep)},
            )
        pawn_rank = 4 if position.side is Color.WHITE else 3
        pawn_square = Square(pawn_rank * 8 + file_of(position.ep))
        pawn = position.piece_at(pawn_square)
        expected_pawn = 9 if position.side is Color.WHITE else 1
        if int(pawn) != expected_pawn:
            raise InvalidFenError(
                "En-passant square has no pawn that could have just double-pushed.",
                context={"ep": square_name(position.ep)},
            )
        if position.halfmove != 0:
            raise InvalidFenError("En-passant position must have a halfmove clock of 0.")

    if in_check(position, position.side.opposite):
        raise InvalidFenError(
            "The side not to move is in check; the position is illegal.",
            hint="Use strict=False for counterfactual positions.",
        )


def to_fen(position: Position) -> str:
    rows: list[str] = []
    for rank_index in range(7, -1, -1):
        row: list[str] = []
        empty = 0
        for file_index in range(8):
            value = position.mailbox[rank_index * 8 + file_index]
            if not value:
                empty += 1
                continue
            if empty:
                row.append(str(empty))
                empty = 0
            row.append(piece_to_char(Piece(value)))
        if empty:
            row.append(str(empty))
        rows.append("".join(row))
    placement = "/".join(rows)

    side = "w" if position.side is Color.WHITE else "b"
    castling = "".join(char for mask, char in _CASTLING_CHARS if position.castling & mask) or "-"
    if position.ep is not None and has_legal_en_passant(position):
        ep = square_name(position.ep)
    else:
        ep = "-"
    return f"{placement} {side} {castling} {ep} {position.halfmove} {position.fullmove}"
