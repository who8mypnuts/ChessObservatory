"""Move ordering heuristics: TT move, MVV-LVA, promotions, killers, history, countermoves (Phase 2, step 4)."""

from __future__ import annotations

from collections.abc import Sequence

from chess_observatory.core.attacks import PIECE_VALUES, see_ge
from chess_observatory.core.moves import (
    MoveFlags,
    move_flags,
    move_from,
    move_is_promotion,
    move_to,
    same_move,
)
from chess_observatory.core.pieces import PieceType, type_of
from chess_observatory.core.position import BoardView


def _mvv_lva_score(position: BoardView, move: int) -> float:
    """MVV-LVA: most valuable victim first, least valuable attacker first."""
    score = 0.0
    if move_flags(move) & MoveFlags.CAPTURE:
        victim = position.piece_at(move_to(move))
        if victim != 0:
            attacker = position.piece_at(move_from(move))
            victim_value = PIECE_VALUES[type_of(victim)]
            attacker_value = PIECE_VALUES[type_of(attacker)] if attacker else 0.0
            score = victim_value - attacker_value / 10.0
    if move_is_promotion(move):
        score += PIECE_VALUES[PieceType.QUEEN]
    return score


def score_move(
    position: BoardView,
    move: int,
    *,
    tt_move: int | None = None,
    killers: Sequence[int] = (),
    history: dict[int, int] | None = None,
    countermoves: dict[int, int] | None = None,
    see_order_bonus: float = 0.0,
) -> float:
    """Heuristic score for a move; higher is searched first."""
    score: float = 0.0
    if see_order_bonus > 0.0 and see_ge(position, move):
        score += see_order_bonus
    if tt_move is not None and same_move(tt_move, move):
        score += 1_000_000.0
    score += _mvv_lva_score(position, move)
    origin = int(move_from(move))
    for killer in killers:
        if int(killer) == origin:
            score += 900.0
            break
    if history:
        score += history.get(move, 0)
    if countermoves:
        score += countermoves.get(move, 0)
    return score


def order_moves(
    position: BoardView,
    moves: Sequence[int],
    *,
    tt_move: int | None = None,
    killers: Sequence[int] = (),
    history: dict[int, int] | None = None,
    countermoves: dict[int, int] | None = None,
    see_order_bonus: float = 0.0,
) -> list[int]:
    """Return the moves sorted by descending heuristic score, stable for ties."""
    scored = [
        (
            score_move(
                position,
                move,
                tt_move=tt_move,
                killers=killers,
                history=history,
                countermoves=countermoves,
                see_order_bonus=see_order_bonus,
            ),
            move,
        )
        for move in moves
    ]
    scored.sort(key=lambda item: -item[0])
    return [move for _score, move in scored]
