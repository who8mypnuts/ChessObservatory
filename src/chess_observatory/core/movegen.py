"""Legal move generation (plan Phase 1, step 7).

Legality is computed directly, not by trying every pseudo-legal move:

* checkers are found once; double check allows king moves only;
* a single check restricts non-king moves to capturing the checker or blocking;
* absolute pins restrict a pinned piece to its pin ray;
* king destinations are tested against enemy attacks with the king removed from
  the occupancy;
* en passant is verified by simulating the double pawn removal, because it is
  the one move whose king-safety effect cannot be read from the current board.

The pseudo-legal generator exists for tests, SAN and analysis code that needs
"moves that follow the piece rules" rather than "moves that are legal".
"""

from __future__ import annotations

from chess_observatory.core.attacks import (
    PAWN_ATTACKS,
    absolute_pins,
    attacks_from,
    checkers,
    in_check,
    is_square_attacked,
)
from chess_observatory.core.make import Board
from chess_observatory.core.moves import (
    MoveFlags,
    MoveList,
    move_flags,
    move_from_uci,
    pack_move,
    same_move,
)
from chess_observatory.core.pieces import Color, PieceType, make_piece, type_of
from chess_observatory.core.position import BoardView
from chess_observatory.core.squares import (
    BETWEEN,
    FULL_BB,
    KING_ATTACKS,
    Square,
    rank_of,
    square_bb,
    squares,
)
from chess_observatory.errors import IllegalMoveError

PROMOTION_TYPES = (PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN)


def _add(
    moves: MoveList,
    origin: Square,
    target: Square,
    flags: MoveFlags = MoveFlags.NONE,
    promotion: PieceType | int = 0,
) -> None:
    moves.append(pack_move(origin, target, promotion, flags))


def _add_pawn_move(
    moves: MoveList,
    origin: Square,
    target: Square,
    *,
    capture: bool,
) -> None:
    rank = rank_of(target)
    if rank in {0, 7}:
        flags = MoveFlags.PROMOTION | (MoveFlags.CAPTURE if capture else MoveFlags.NONE)
        for promotion in PROMOTION_TYPES:
            _add(moves, origin, target, flags, promotion)
    else:
        _add(moves, origin, target, MoveFlags.CAPTURE if capture else MoveFlags.NONE)


def generate_pseudo_legal(position: BoardView) -> MoveList:
    moves = MoveList()
    side = position.side
    own = position.color_occupancy(side)
    enemy = position.color_occupancy(side.opposite)
    enemy_king = position.pieces(side.opposite, PieceType.KING)
    occupancy = position.occupancy
    empty = ~occupancy & FULL_BB

    pawns = position.pieces(side, PieceType.PAWN)
    direction = 8 if side is Color.WHITE else -8
    for origin in squares(pawns):
        one = int(origin) + direction
        if 0 <= one < 64 and empty & square_bb(Square(one)):
            _add_pawn_move(moves, origin, Square(one), capture=False)
            start_rank = 1 if side is Color.WHITE else 6
            if rank_of(origin) == start_rank:
                two = one + direction
                if empty & square_bb(Square(two)):
                    _add(moves, origin, Square(two), MoveFlags.DOUBLE_PUSH)
        for target in squares(PAWN_ATTACKS[int(side)][int(origin)] & enemy & ~enemy_king):
            _add_pawn_move(moves, origin, target, capture=True)
        if position.ep is not None and PAWN_ATTACKS[int(side)][int(origin)] & square_bb(
            position.ep
        ):
            _add(
                moves,
                origin,
                position.ep,
                MoveFlags.CAPTURE | MoveFlags.EN_PASSANT,
            )

    for piece_type in (PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
        for origin in squares(position.pieces(side, piece_type)):
            targets = attacks_from(position, origin, occupancy) & ~own & ~enemy_king
            for target in squares(targets):
                flags = MoveFlags.CAPTURE if enemy & square_bb(target) else MoveFlags.NONE
                _add(moves, origin, target, flags)

    king = position.king_square(side)
    if king is not None:
        for target in squares(KING_ATTACKS[int(king)] & ~own & ~enemy_king):
            flags = MoveFlags.CAPTURE if enemy & square_bb(target) else MoveFlags.NONE
            _add(moves, king, target, flags)
        _castling_moves(position, moves, king, occupancy, enemy, check_safety=False)

    return moves


def _castling_moves(
    position: BoardView,
    moves: MoveList,
    king: Square,
    occupancy: int,
    enemy: int,
    *,
    check_safety: bool,
) -> None:
    side = position.side
    if side is Color.WHITE:
        home, kingside_rook, queenside_rook = Square(4), Square(7), Square(0)
        king_side_empty = square_bb(Square(5)) | square_bb(Square(6))
        queen_side_empty = square_bb(Square(1)) | square_bb(Square(2)) | square_bb(Square(3))
        king_side_target, queen_side_target = Square(6), Square(2)
        transit_king, transit_queen = Square(5), Square(3)
        king_right, queen_right = 1, 2
    else:
        home, kingside_rook, queenside_rook = Square(60), Square(63), Square(56)
        king_side_empty = square_bb(Square(61)) | square_bb(Square(62))
        queen_side_empty = square_bb(Square(57)) | square_bb(Square(58)) | square_bb(Square(59))
        king_side_target, queen_side_target = Square(62), Square(58)
        transit_king, transit_queen = Square(61), Square(59)
        king_right, queen_right = 4, 8

    if king != home or position.piece_at(home) != _king_of(side):
        return
    occupancy_without_king = occupancy ^ square_bb(king)

    if (
        position.castling & king_right
        and position.piece_at(kingside_rook) == _rook_of(side)
        and not occupancy & king_side_empty
        and (
            not check_safety
            or (
                not is_square_attacked(
                    position, transit_king, side.opposite, occupancy_without_king
                )
                and not is_square_attacked(
                    position, king_side_target, side.opposite, occupancy_without_king
                )
            )
        )
    ):
        _add(moves, king, king_side_target, MoveFlags.CASTLE)

    if (
        position.castling & queen_right
        and position.piece_at(queenside_rook) == _rook_of(side)
        and not occupancy & queen_side_empty
        and (
            not check_safety
            or (
                not is_square_attacked(
                    position, transit_queen, side.opposite, occupancy_without_king
                )
                and not is_square_attacked(
                    position, queen_side_target, side.opposite, occupancy_without_king
                )
            )
        )
    ):
        _add(moves, king, queen_side_target, MoveFlags.CASTLE)


def _king_of(color: Color) -> int:
    return int(make_piece(color, PieceType.KING))


def _rook_of(color: Color) -> int:
    return int(make_piece(color, PieceType.ROOK))


def _king_moves(
    position: BoardView,
    moves: MoveList,
    king: Square,
    occupancy: int,
    enemy: int,
) -> None:
    own = position.color_occupancy(position.side)
    enemy_king = position.pieces(position.side.opposite, PieceType.KING)
    occupancy_without_king = occupancy ^ square_bb(king)
    for target in squares(KING_ATTACKS[int(king)] & ~own & ~enemy_king):
        if is_square_attacked(position, target, position.side.opposite, occupancy_without_king):
            continue
        flags = MoveFlags.CAPTURE if enemy & square_bb(target) else MoveFlags.NONE
        _add(moves, king, target, flags)


def generate_legal(position: BoardView) -> MoveList:
    moves = MoveList()
    side = position.side
    king = position.king_square(side)
    if king is None:
        # Non-strict position: no king to endanger, so piece rules are the only
        # rules that apply. The edit that produced it carries the report.
        return generate_pseudo_legal(position)

    occupancy = position.occupancy
    enemy = position.color_occupancy(side.opposite)
    checkers_bb = checkers(position, side)
    if checkers_bb.bit_count() >= 2:
        _king_moves(position, moves, king, occupancy, enemy)
        return moves

    if checkers_bb:
        checker = Square((checkers_bb & -checkers_bb).bit_length() - 1)
        check_mask = BETWEEN[int(king)][int(checker)] | square_bb(checker)
    else:
        check_mask = FULL_BB

    pins = absolute_pins(position, side)
    pin_rays = [0] * 64
    for pin in pins:
        pin_rays[int(pin.square)] = pin.ray

    _pawn_moves(position, moves, king, check_mask, pin_rays)
    _piece_moves(position, moves, check_mask, pin_rays)
    _king_moves(position, moves, king, occupancy, enemy)
    if not checkers_bb:
        _castling_moves(position, moves, king, occupancy, enemy, check_safety=True)
    return moves


def _pawn_moves(
    position: BoardView,
    moves: MoveList,
    king: Square,
    check_mask: int,
    pin_rays: list[int],
) -> None:
    side = position.side
    enemy = position.color_occupancy(side.opposite)
    enemy_king = position.pieces(side.opposite, PieceType.KING)
    occupancy = position.occupancy
    empty = ~occupancy & FULL_BB
    direction = 8 if side is Color.WHITE else -8
    start_rank = 1 if side is Color.WHITE else 6

    for origin in squares(position.pieces(side, PieceType.PAWN)):
        allowed = check_mask & (pin_rays[int(origin)] or FULL_BB)
        one = int(origin) + direction
        one_empty = 0 <= one < 64 and bool(empty & square_bb(Square(one)))
        if one_empty and square_bb(Square(one)) & allowed:
            _add_pawn_move(moves, origin, Square(one), capture=False)
        if one_empty and rank_of(origin) == start_rank:
            two = one + direction
            if (
                0 <= two < 64
                and empty & square_bb(Square(two))
                and square_bb(Square(two)) & allowed
            ):
                _add(moves, origin, Square(two), MoveFlags.DOUBLE_PUSH)

        for target in squares(PAWN_ATTACKS[int(side)][int(origin)] & enemy & ~enemy_king):
            if square_bb(target) & allowed:
                _add_pawn_move(moves, origin, target, capture=True)

        ep = position.ep
        if ep is None or not (PAWN_ATTACKS[int(side)][int(origin)] & square_bb(ep)):
            continue
        captured_square = Square(int(ep) - direction)
        captured = position.piece_at(captured_square)
        if captured == 0 or type_of(captured) is not PieceType.PAWN:
            continue
        simulated = (occupancy ^ square_bb(origin) ^ square_bb(captured_square)) | square_bb(ep)
        if not is_square_attacked(position, king, side.opposite, simulated):
            _add(moves, origin, ep, MoveFlags.CAPTURE | MoveFlags.EN_PASSANT)


def _piece_moves(
    position: BoardView,
    moves: MoveList,
    check_mask: int,
    pin_rays: list[int],
) -> None:
    side = position.side
    own = position.color_occupancy(side)
    enemy = position.color_occupancy(side.opposite)
    enemy_king = position.pieces(side.opposite, PieceType.KING)
    occupancy = position.occupancy
    for piece_type in (PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
        for origin in squares(position.pieces(side, piece_type)):
            allowed = check_mask & (pin_rays[int(origin)] or FULL_BB)
            targets = attacks_from(position, origin, occupancy) & ~own & ~enemy_king & allowed
            for target in squares(targets):
                flags = MoveFlags.CAPTURE if enemy & square_bb(target) else MoveFlags.NONE
                _add(moves, origin, target, flags)


def find_legal(position: BoardView, move: int) -> int | None:
    """Return the generated move with the same identity, flags included."""
    for candidate in generate_legal(position):
        if same_move(candidate, move):
            return candidate
    return None


def is_legal(position: BoardView, move: int) -> bool:
    return find_legal(position, move) is not None


def legal_move_from_uci(position: BoardView, text: str) -> int:
    """Resolve a UCI string to a fully flagged legal move."""
    move = move_from_uci(text)
    resolved = find_legal(position, move)
    if resolved is None:
        raise IllegalMoveError(
            f"illegal move {text!r} in {position!r}",
            context={"move": text},
        )
    return resolved


def is_checkmate(position: BoardView) -> bool:
    """The side to move is in check and has no legal move."""
    return in_check(position, position.side) and not generate_legal(position)


def is_stalemate(position: BoardView) -> bool:
    """The side to move is not in check and has no legal move."""
    return not in_check(position, position.side) and not generate_legal(position)


def is_game_over(position: BoardView) -> bool:
    """No legal moves remain, regardless of check."""
    return not generate_legal(position)


def has_legal_en_passant(position: BoardView) -> bool:
    """True when the side to move has a legal en-passant capture."""
    if position.ep is None:
        return False
    return any(move_flags(move) & MoveFlags.EN_PASSANT for move in generate_legal(position))


def perft(position: BoardView, depth: int) -> int:
    """Count legal move sequences to ``depth``."""
    if depth <= 0:
        return 1
    board = position if isinstance(position, Board) else Board.from_position(position)
    moves = generate_legal(board)
    if depth == 1:
        return len(moves)
    total = 0
    for move in moves:
        board.make(move)
        total += perft(board, depth - 1)
        board.unmake()
    return total


def perft_divide(position: BoardView, depth: int) -> dict[str, int]:
    """Per-root-move counts, the standard way to locate a perft discrepancy."""
    from chess_observatory.core.moves import move_to_uci

    board = position if isinstance(position, Board) else Board.from_position(position)
    if depth <= 0:
        return {"": 1}
    result: dict[str, int] = {}
    for move in generate_legal(board):
        board.make(move)
        result[move_to_uci(move)] = perft(board, depth - 1)
        board.unmake()
    return result
