"""Attack generation, pins, checks, x-rays and SEE (plan Phase 1, step 6).

There is exactly one implementation of "what attacks this square" in the
project. Legality, tactics, influence, king safety and every visual call these
functions; nothing recomputes attackers locally (plan §6.2).

The :class:`AttackMap` is the rich, cached view used by analysis and the UI. Move
generation uses the cheaper :func:`attackers_to` and :func:`is_square_attacked`
directly, so perft does not pay for the full map.
"""

from __future__ import annotations

from collections import OrderedDict
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
    DIAGONAL_TYPES,
    ORTHOGONAL_TYPES,
    Color,
    PieceType,
    color_of,
    type_of,
)
from chess_observatory.core.position import BoardView, Position
from chess_observatory.core.squares import (
    EAST,
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    NORTH,
    NORTH_EAST,
    NORTH_WEST,
    RAYS,
    SOUTH,
    SOUTH_EAST,
    SOUTH_WEST,
    WEST,
    Bitboard,
    Square,
    lsb,
    msb,
    square_bb,
    squares,
)
from chess_observatory.core.zobrist import compute_key, variant_key

DIAGONAL_DIRECTIONS: Final = (NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST)
ORTHOGONAL_DIRECTIONS: Final = (NORTH, EAST, SOUTH, WEST)
ASCENDING_DIRECTIONS: Final = frozenset({NORTH, NORTH_EAST, EAST, NORTH_WEST})

PIECE_VALUES: Final[dict[PieceType, int]] = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.KING: 20_000,
}

MAX_CACHED_MAPS: Final = 2048


def _build_pawn_attacks(color: Color) -> tuple[int, ...]:
    result: list[int] = []
    rank_delta = 1 if color is Color.WHITE else -1
    for square in range(64):
        file_index = square & 7
        rank_index = square >> 3
        attacks = 0
        for file_delta in (-1, 1):
            target_file = file_index + file_delta
            target_rank = rank_index + rank_delta
            if 0 <= target_file < 8 and 0 <= target_rank < 8:
                attacks |= 1 << (target_rank * 8 + target_file)
        result.append(attacks)
    return tuple(result)


PAWN_ATTACKS: Final = (
    _build_pawn_attacks(Color.WHITE),
    _build_pawn_attacks(Color.BLACK),
)


def _nearest(bitboard: Bitboard, direction: int) -> Square:
    return lsb(bitboard) if direction in ASCENDING_DIRECTIONS else msb(bitboard)


def _ray_attacks(square: Square, occupancy: int, directions: tuple[int, ...]) -> int:
    result = 0
    for direction in directions:
        ray = RAYS[direction][int(square)]
        blockers = ray & occupancy
        if blockers:
            first = _nearest(blockers, direction)
            ray ^= RAYS[direction][int(first)]
        result |= ray
    return result


def pawn_attacks(color: Color, square: Square) -> int:
    return PAWN_ATTACKS[int(color)][int(square)]


def knight_attacks(square: Square) -> int:
    return KNIGHT_ATTACKS[int(square)]


def king_attacks(square: Square) -> int:
    return KING_ATTACKS[int(square)]


def bishop_attacks(square: Square, occupancy: int) -> int:
    return _ray_attacks(square, occupancy, DIAGONAL_DIRECTIONS)


def rook_attacks(square: Square, occupancy: int) -> int:
    return _ray_attacks(square, occupancy, ORTHOGONAL_DIRECTIONS)


def queen_attacks(square: Square, occupancy: int) -> int:
    return bishop_attacks(square, occupancy) | rook_attacks(square, occupancy)


def attacks_from(position: BoardView, square: Square, occupancy: int | None = None) -> int:
    """Every square attacked by the piece standing on ``square``."""
    piece = position.piece_at(square)
    if piece == 0:
        return 0
    occ = position.occupancy if occupancy is None else occupancy
    color = color_of(piece)
    piece_type = type_of(piece)
    if piece_type is PieceType.PAWN:
        return pawn_attacks(color, square)
    if piece_type is PieceType.KNIGHT:
        return KNIGHT_ATTACKS[int(square)]
    if piece_type is PieceType.BISHOP:
        return bishop_attacks(square, occ)
    if piece_type is PieceType.ROOK:
        return rook_attacks(square, occ)
    if piece_type is PieceType.QUEEN:
        return queen_attacks(square, occ)
    return KING_ATTACKS[int(square)]


def attackers_to_color(
    position: BoardView,
    square: Square,
    color: Color,
    occupancy: int | None = None,
) -> int:
    """Pieces of ``color`` that attack ``square`` under ``occupancy``."""
    occ = position.occupancy if occupancy is None else occupancy
    pieces = position.pieces
    # Mask every piece board by the supplied occupancy: callers pass a
    # simulated occupancy where a captured piece (notably an en-passant pawn)
    # has already been removed.
    attackers = PAWN_ATTACKS[int(color.opposite)][int(square)] & pieces(color, PieceType.PAWN) & occ
    attackers |= KNIGHT_ATTACKS[int(square)] & pieces(color, PieceType.KNIGHT) & occ
    attackers |= KING_ATTACKS[int(square)] & pieces(color, PieceType.KING) & occ
    diagonal = bishop_attacks(square, occ)
    orthogonal = rook_attacks(square, occ)
    attackers |= diagonal & (pieces(color, PieceType.BISHOP) | pieces(color, PieceType.QUEEN)) & occ
    attackers |= orthogonal & (pieces(color, PieceType.ROOK) | pieces(color, PieceType.QUEEN)) & occ
    return attackers


def attackers_to(
    position: BoardView,
    square: Square,
    occupancy: int | None = None,
) -> int:
    """All pieces, of either colour, that attack ``square``."""
    return attackers_to_color(position, square, Color.WHITE, occupancy) | attackers_to_color(
        position, square, Color.BLACK, occupancy
    )


def is_square_attacked(
    position: BoardView,
    square: Square,
    by_color: Color,
    occupancy: int | None = None,
) -> bool:
    return bool(attackers_to_color(position, square, by_color, occupancy))


def checkers(position: BoardView, color: Color | None = None) -> int:
    """Pieces giving check to ``color`` (default: the side to move)."""
    side = position.side if color is None else color
    king = position.king_square(side)
    if king is None:
        return 0
    return attackers_to_color(position, king, side.opposite)


def in_check(position: BoardView, color: Color | None = None) -> bool:
    return bool(checkers(position, color))


@dataclass(frozen=True, slots=True)
class Pin:
    """A piece of ``color`` shielding a more valuable own piece from a slider.

    ``square`` is the front piece, ``attacker`` the enemy slider and ``ray`` the
    whole line through the front piece. An absolute pin shields the king and
    restricts legality; a relative pin only restricts material safety.
    """

    color: Color
    square: Square
    attacker: Square
    ray: int


@dataclass(frozen=True, slots=True)
class Discovered:
    """A piece whose move would uncover a check on the opposing king."""

    color: Color
    square: Square
    king: Square
    slider: Square
    ray: int


@dataclass(frozen=True, slots=True)
class AttackMap:
    """Cached attack facts for one position.

    ``attackers[color][square]`` is the bitboard of pieces of ``color`` that
    attack ``square``. ``attacks[color]`` is the union of squares that colour
    attacks. ``safe[color]`` is the set of squares that colour can occupy with a
    non-losing exchange (SEE >= 0).
    """

    key: int
    attackers: tuple[tuple[int, ...], tuple[int, ...]]
    attacks: tuple[int, int]
    checkers: tuple[int, int]
    pins: tuple[Pin, ...]
    relative_pins: tuple[Pin, ...]
    discovered: tuple[Discovered, ...]
    xray: tuple[tuple[int, ...], tuple[int, ...]]
    safe: tuple[int, int]

    def attackers_to(self, square: Square, color: Color | None = None) -> int:
        if color is None:
            return self.attackers[0][int(square)] | self.attackers[1][int(square)]
        return self.attackers[int(color)][int(square)]

    def is_attacked(self, square: Square, color: Color | None = None) -> bool:
        return bool(self.attackers_to(square, color))

    def defenders_of(self, position: BoardView, square: Square) -> int:
        piece = position.piece_at(square)
        if piece == 0:
            return 0
        return self.attackers_to(square, color_of(piece))

    def pins_for(self, color: Color) -> tuple[Pin, ...]:
        return tuple(pin for pin in self.pins if pin.color is color)

    def relative_pins_for(self, color: Color) -> tuple[Pin, ...]:
        return tuple(pin for pin in self.relative_pins if pin.color is color)

    def pin_ray(self, square: Square) -> int:
        for pin in self.pins:
            if pin.square == square:
                return pin.ray
        return 0

    def relative_pin_ray(self, square: Square) -> int:
        for pin in self.relative_pins:
            if pin.square == square:
                return pin.ray
        return 0

    def safe_for(self, color: Color) -> int:
        return self.safe[int(color)]

    def discovered_for(self, color: Color) -> tuple[Discovered, ...]:
        return tuple(item for item in self.discovered if item.color is color)

    def xray_from(self, square: Square, color: Color) -> int:
        return self.xray[int(color)][int(square)]


def absolute_pins(position: BoardView, color: Color) -> tuple[Pin, ...]:
    king = position.king_square(color)
    if king is None:
        return ()
    occupancy = position.occupancy
    own = position.color_occupancy(color)
    pins: list[Pin] = []
    for direction in range(8):
        ray = RAYS[direction][int(king)]
        blockers = ray & occupancy
        if not blockers:
            continue
        first = _nearest(blockers, direction)
        if not square_bb(first) & own:
            continue
        beyond = RAYS[direction][int(first)] & occupancy
        if not beyond:
            continue
        second = _nearest(beyond, direction)
        piece = position.piece_at(second)
        if piece == 0 or color_of(piece) is color:
            continue
        piece_type = type_of(piece)
        if direction in DIAGONAL_DIRECTIONS:
            is_slider = piece_type in DIAGONAL_TYPES
        else:
            is_slider = piece_type in ORTHOGONAL_TYPES
        if not is_slider:
            continue
        ray_mask = RAYS[direction][int(king)] | RAYS[(direction + 4) % 8][int(king)]
        ray_mask &= ~square_bb(king)
        pins.append(Pin(color=color, square=first, attacker=second, ray=ray_mask))
    return tuple(pins)


def relative_pins(position: BoardView, color: Color) -> tuple[Pin, ...]:
    """Own pieces shielding a more valuable own piece from an enemy slider.

    Moving a relatively pinned piece is legal, but it loses material. Absolute
    pins (against the king) are excluded; they are reported by
    :func:`absolute_pins`. The two sets are disjoint.
    """
    own = position.color_occupancy(color)
    occupancy = position.occupancy
    pins: list[Pin] = []
    for slider_square in squares(position.color_occupancy(color.opposite)):
        slider_type = type_of(position.piece_at(slider_square))
        directions: tuple[int, ...]
        if slider_type is PieceType.BISHOP:
            directions = DIAGONAL_DIRECTIONS
        elif slider_type is PieceType.ROOK:
            directions = ORTHOGONAL_DIRECTIONS
        elif slider_type is PieceType.QUEEN:
            directions = DIAGONAL_DIRECTIONS + ORTHOGONAL_DIRECTIONS
        else:
            continue
        for direction in directions:
            blockers = RAYS[direction][int(slider_square)] & occupancy
            if not blockers:
                continue
            front_square = _nearest(blockers, direction)
            if not square_bb(front_square) & own:
                continue
            beyond = RAYS[direction][int(front_square)] & occupancy
            if not beyond:
                continue
            back_square = _nearest(beyond, direction)
            if not square_bb(back_square) & own:
                continue
            back_type = type_of(position.piece_at(back_square))
            if back_type is PieceType.KING:
                continue
            front_type = type_of(position.piece_at(front_square))
            if PIECE_VALUES[front_type] >= PIECE_VALUES[back_type]:
                continue
            ray_mask = (
                RAYS[direction][int(front_square)] | RAYS[(direction + 4) % 8][int(front_square)]
            ) & ~square_bb(front_square)
            pins.append(
                Pin(
                    color=color,
                    square=front_square,
                    attacker=slider_square,
                    ray=ray_mask,
                )
            )
    return tuple(pins)


def _discovered_checks(position: BoardView, color: Color) -> tuple[Discovered, ...]:
    """Pieces of ``color`` whose move would uncover a check on the enemy king."""
    enemy_king = position.king_square(color.opposite)
    if enemy_king is None:
        return ()
    occupancy = position.occupancy
    own = position.color_occupancy(color)
    found: list[Discovered] = []
    for direction in range(8):
        ray = RAYS[direction][int(enemy_king)]
        blockers = ray & occupancy
        if not blockers:
            continue
        first = _nearest(blockers, direction)
        if not square_bb(first) & own:
            continue
        beyond = RAYS[direction][int(first)] & occupancy
        if not beyond:
            continue
        second = _nearest(beyond, direction)
        piece = position.piece_at(second)
        if piece == 0 or color_of(piece) is not color:
            continue
        piece_type = type_of(piece)
        is_slider = (
            piece_type in DIAGONAL_TYPES
            if direction in DIAGONAL_DIRECTIONS
            else piece_type in ORTHOGONAL_TYPES
        )
        if not is_slider:
            continue
        line = RAYS[direction][int(enemy_king)] | RAYS[(direction + 4) % 8][int(enemy_king)]
        found.append(
            Discovered(
                color=color,
                square=first,
                king=enemy_king,
                slider=second,
                ray=line & ~square_bb(enemy_king),
            )
        )
    return tuple(found)


def _xray_table(position: BoardView, color: Color) -> tuple[int, ...]:
    occupancy = position.occupancy
    table = [0] * 64
    for square in squares(
        position.pieces(color, PieceType.BISHOP)
        | position.pieces(color, PieceType.ROOK)
        | position.pieces(color, PieceType.QUEEN)
    ):
        piece_type = type_of(position.piece_at(square))
        directions = (
            DIAGONAL_DIRECTIONS
            if piece_type is PieceType.BISHOP
            else ORTHOGONAL_DIRECTIONS
            if piece_type is PieceType.ROOK
            else DIAGONAL_DIRECTIONS + ORTHOGONAL_DIRECTIONS
        )
        through = 0
        for direction in directions:
            blockers = RAYS[direction][int(square)] & occupancy
            if blockers:
                first = _nearest(blockers, direction)
                through |= RAYS[direction][int(first)]
        table[int(square)] = through
    return tuple(table)


def _least_valuable_attacker(
    position: BoardView,
    target: Square,
    color: Color,
    occupancy: int,
) -> Square | None:
    attackers = attackers_to_color(position, target, color, occupancy) & occupancy
    best: Square | None = None
    best_value = 1 << 30
    for square in squares(attackers):
        piece = position.piece_at(square)
        if piece == 0:
            continue
        value = PIECE_VALUES[type_of(piece)]
        if value < best_value:
            best = square
            best_value = value
    return best


def _see_recursive(
    position: BoardView,
    target: Square,
    color: Color,
    occupancy: int,
    target_value: int,
) -> int:
    attacker = _least_valuable_attacker(position, target, color, occupancy)
    if attacker is None:
        return 0
    attacker_value = PIECE_VALUES[type_of(position.piece_at(attacker))]
    new_occupancy = (occupancy ^ square_bb(attacker)) | square_bb(target)
    return target_value - _see_recursive(
        position, target, color.opposite, new_occupancy, attacker_value
    )


def see_ge(position: BoardView, move: int, threshold: int = 0) -> bool:
    """Static exchange evaluation: is the move worth at least ``threshold``?

    The initial move may be a capture, an en-passant capture or a promotion.
    Quiet moves have a static value of zero.
    """
    target = move_to(move)
    origin = move_from(move)
    flags = move_flags(move)
    captured = position.piece_at(target)
    occupancy = position.occupancy
    gain = 0
    if flags & MoveFlags.CAPTURE:
        if captured != 0:
            gain = PIECE_VALUES[type_of(captured)]
        if flags & MoveFlags.EN_PASSANT:
            direction = 1 if color_of(position.piece_at(origin)) is Color.WHITE else -1
            captured_square = Square(int(target) - 8 * direction)
            occupancy ^= square_bb(captured_square)
            gain = PIECE_VALUES[PieceType.PAWN]
    elif not move_promotion(move):
        return threshold <= 0
    promotion = move_promotion(move)
    if promotion is not None:
        gain += PIECE_VALUES[promotion] - PIECE_VALUES[PieceType.PAWN]
    mover = color_of(position.piece_at(origin))
    occupancy = (occupancy ^ square_bb(origin)) | square_bb(target)
    attacker_value = PIECE_VALUES[type_of(position.piece_at(origin))]
    net = gain - _see_recursive(position, target, mover.opposite, occupancy, attacker_value)
    return net >= threshold


def see_square(position: BoardView, target: Square, color: Color) -> int:
    """Best static exchange value for ``color`` moving onto ``target``.

    Returns a large negative number when ``color`` has no attacker.
    """
    occupancy = position.occupancy
    attacker = _least_valuable_attacker(position, target, color, occupancy)
    if attacker is None:
        return -(1 << 30)
    victim = position.piece_at(target)
    if victim != 0 and color_of(victim) is color:
        return -(1 << 30)
    gain = PIECE_VALUES[type_of(victim)] if victim != 0 else 0
    attacker_value = PIECE_VALUES[type_of(position.piece_at(attacker))]
    new_occupancy = (occupancy ^ square_bb(attacker)) | square_bb(target)
    return gain - _see_recursive(position, target, color.opposite, new_occupancy, attacker_value)


def _build_attack_map(position: Position) -> AttackMap:
    occupancy = position.occupancy
    attackers: list[list[int]] = [[0] * 64, [0] * 64]
    attacks = [0, 0]
    for color in Color:
        color_index = int(color)
        for square in squares(position.color_occupancy(color)):
            piece_attacks = attacks_from(position, square, occupancy)
            attacks[color_index] |= piece_attacks
            attacker_bit = square_bb(square)
            for target in squares(piece_attacks):
                attackers[color_index][int(target)] |= attacker_bit

    pins = absolute_pins(position, Color.WHITE) + absolute_pins(position, Color.BLACK)
    relative = relative_pins(position, Color.WHITE) + relative_pins(position, Color.BLACK)
    discovered = _discovered_checks(position, Color.WHITE) + _discovered_checks(
        position, Color.BLACK
    )
    xray = (_xray_table(position, Color.WHITE), _xray_table(position, Color.BLACK))

    safe = [0, 0]
    for color in Color:
        color_index = int(color)
        candidates = attacks[color_index] & ~position.color_occupancy(color)
        for square in squares(candidates):
            if see_square(position, square, color) >= 0:
                safe[color_index] |= square_bb(square)

    return AttackMap(
        key=compute_key(position),
        attackers=(tuple(attackers[0]), tuple(attackers[1])),
        attacks=(attacks[0], attacks[1]),
        checkers=(
            checkers(position, Color.WHITE),
            checkers(position, Color.BLACK),
        ),
        pins=pins,
        relative_pins=relative,
        discovered=discovered,
        xray=xray,
        safe=(safe[0], safe[1]),
    )


_MAP_CACHE: OrderedDict[tuple[int, tuple[bool, str]], tuple[Position, AttackMap]] = OrderedDict()


def attack_map(position: Position) -> AttackMap:
    """Return the cached attack map for ``position``.

    The plan keys the cache by ``(zobrist, variant_key)``. A full position
    equality check on hit makes the cache collision-proof without giving up the
    cheap key.
    """
    key = (compute_key(position), variant_key(position))
    cached = _MAP_CACHE.get(key)
    if cached is not None and cached[0] == position:
        _MAP_CACHE.move_to_end(key)
        return cached[1]
    result = _build_attack_map(position)
    _MAP_CACHE[key] = (position, result)
    if len(_MAP_CACHE) > MAX_CACHED_MAPS:
        _MAP_CACHE.popitem(last=False)
    return result


def clear_attack_cache() -> None:
    _MAP_CACHE.clear()
