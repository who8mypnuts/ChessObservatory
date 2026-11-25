"""Own engine: negamax, alpha-beta, qsearch, mate scores (Phase 2, step 5)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from chess_observatory.core.attacks import in_check, see_ge
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal
from chess_observatory.core.moves import MoveFlags, move_flags, move_is_promotion
from chess_observatory.core.position import BoardView
from chess_observatory.search.limits import SearchLimits
from chess_observatory.search.ordering import order_moves
from chess_observatory.search.tt import Bound, TranspositionTable, TTEntry

MATE_SCORE = 1_000_000.0


@dataclass(frozen=True, slots=True)
class SearchContext:
    """Everything a bounded search needs from its surroundings."""

    limits: SearchLimits
    tt: TranspositionTable
    evaluate: Callable[[BoardView], float]
    is_draw: Callable[[BoardView], bool] | None = None
    max_depth: int = 0


def qsearch(board: Board, alpha: float, beta: float, ply: int, ctx: SearchContext) -> float:
    """Quiescence search with stand pat, draw detection and delta pruning."""
    if ctx.is_draw is not None and ctx.is_draw(board):
        ctx.tt.store(TTEntry(key=board.key, depth=0, flag=Bound.EXACT, value=0.0))
        return 0.0
    stand_pat = ctx.evaluate(board)
    if stand_pat >= beta:
        ctx.tt.store(TTEntry(key=board.key, depth=0, flag=Bound.UPPER, value=stand_pat))
        return stand_pat
    if stand_pat > alpha:
        alpha = stand_pat
    moves = list(generate_legal(board))
    if not moves:
        return -MATE_SCORE + ply if in_check(board) else 0.0
    ordered = order_moves(board, moves)
    alpha_original = alpha
    best = float("-inf")
    for move in ordered:
        quiet = not move_is_promotion(move) and not (move_flags(move) & MoveFlags.CAPTURE)
        capture = (move_flags(move) & MoveFlags.CAPTURE) != 0
        if quiet and stand_pat <= alpha:
            continue
        if capture and not see_ge(board, move, int(alpha - stand_pat)):
            continue
        board.make(move)
        score = -qsearch(board, -beta, -alpha, ply + 1, ctx)
        board.unmake()
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    if best == float("-inf"):
        best = stand_pat
    flag = (
        Bound.EXACT
        if alpha_original < beta and best < beta
        else (Bound.LOWER if best >= beta else Bound.UPPER)
    )
    ctx.tt.store(TTEntry(key=board.key, depth=0, flag=flag, value=best))
    return best


def _node(
    board: Board,
    alpha: float,
    beta: float,
    depth: int,
    ply: int,
    ctx: SearchContext,
) -> tuple[float, list[int]]:
    """Negamax alpha-beta with transposition table and principal-line extraction."""
    if ctx.is_draw is not None and ctx.is_draw(board):
        return (0.0, [])
    tt = ctx.tt.lookup(board.key, depth) if depth > 0 else None
    if tt is not None:
        if tt.flag is Bound.EXACT:
            return (tt.value, [])
        if tt.flag is Bound.LOWER:
            beta = min(beta, tt.value)
            if beta <= alpha:
                return (tt.value, [])
        else:
            alpha = max(alpha, tt.value)
            if alpha >= beta:
                return (tt.value, [])
    if depth <= 0:
        return (qsearch(board, alpha, beta, ply, ctx), [])
    moves = order_moves(board, list(generate_legal(board)))
    if not moves:
        return ((-MATE_SCORE + ply) if in_check(board) else 0.0, [])
    best = float("-inf")
    best_move: int | None = None
    best_line: list[int] = []
    alpha_original = alpha
    for move in moves:
        board.make(move)
        score, line = _node(board, -beta, -alpha, depth - 1, ply + 1, ctx)
        board.unmake()
        score = -score
        if score > best:
            best = score
            best_move = move
            best_line = [move, *line]
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    flag = (
        Bound.EXACT
        if alpha_original < beta and best < beta
        else (Bound.LOWER if best >= beta else Bound.UPPER)
    )
    ctx.tt.store(TTEntry(key=board.key, depth=depth, flag=flag, value=best, move=best_move))
    return (best, best_line)


def negamax(
    board: Board, alpha: float, beta: float, depth: int, ply: int, ctx: SearchContext
) -> float:
    """Negamax alpha-beta score for the side to move; ``board`` must be mutable."""
    return _node(board, alpha, beta, depth, ply, ctx)[0]


def search(
    board: Board,
    ctx: SearchContext,
    *,
    root_moves: Sequence[int] | None = None,
) -> tuple[float, list[int]]:
    """Full-window root search: best score for the side to move and the principal line."""
    moves = list(root_moves) if root_moves is not None else list(generate_legal(board))
    ordered = order_moves(board, moves)
    best_score = float("-inf")
    best_line: list[int] = []
    for move in ordered:
        board.make(move)
        score, line = _node(board, float("-inf"), float("inf"), max(ctx.max_depth - 1, 0), 1, ctx)
        board.unmake()
        score = -score
        if score > best_score:
            best_score = score
            best_line = [move, *line]
    return (best_score, best_line)
