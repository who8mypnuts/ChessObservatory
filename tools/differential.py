#!/usr/bin/env python3
"""Differential harness: the rules core against the ``python-chess`` oracle.

CI runs a small game count on every push; the Phase 1 gate is 2,000 games in CI
and 100,000 games locally::

    uv run python tools/differential.py --games 2000
    uv run python tools/differential.py --games 100000 --san-sample 0

Every position compares the legal move set, checkmate/stalemate status, the
en-passant flag and (optionally) canonical SAN. After every chosen move the FEN
must match the oracle exactly. The first mismatch prints the seed, the game and
ply, the FEN and the offending move, so a regression is reproducible.

``python-chess`` is a development dependency. This script lives in ``tools/``,
never in ``src/``; the import-graph guard enforces the boundary.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass

import chess

from chess_observatory.core.fen import parse_fen, to_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import (
    generate_legal,
    has_legal_en_passant,
    is_checkmate,
    is_stalemate,
    perft,
)
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.san import parse_san, to_san

STARTING_FEN = chess.STARTING_FEN

# The published perft positions (CPW), used by the oracle and by the unit suite.
PERFT_POSITIONS: tuple[tuple[str, str], ...] = (
    ("start", chess.STARTING_FEN),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("position3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"),
    ("position4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"),
    ("position5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"),
    (
        "position6",
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    ),
)

SAMPLE_PGN = """[Event "Oracle"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6
8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0
"""


class DifferentialMismatch(AssertionError):
    """Raised on the first disagreement with the oracle."""


@dataclass(frozen=True, slots=True)
class RunStats:
    """What a run actually covered, printed at the end and used by tests."""

    games: int
    plies: int
    positions: int
    moves_compared: int
    san_compared: int
    seconds: float

    @property
    def games_per_second(self) -> float:
        return self.games / self.seconds if self.seconds else float("inf")

    def describe(self) -> str:
        return (
            f"{self.games} games, {self.plies} plies, {self.positions} positions, "
            f"{self.moves_compared} moves, {self.san_compared} SAN moves, "
            f"{self.seconds:.1f}s ({self.games_per_second:.1f} games/s)"
        )


def _oracle_perft(board: chess.Board, depth: int) -> int:
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves:
        board.push(move)
        total += _oracle_perft(board, depth - 1)
        board.pop()
    return total


def _fail(context: str, detail: str) -> None:
    raise DifferentialMismatch(f"{context}: {detail}")


def compare_position(board: Board, oracle: chess.Board, context: str) -> dict[str, int]:
    """Compare one position; return the oracle's legal moves keyed by UCI."""
    ours = {move_to_uci(move): move for move in generate_legal(board)}
    theirs = {move.uci(): move for move in oracle.legal_moves}
    if ours.keys() != theirs.keys():
        missing = sorted(theirs.keys() - ours.keys())
        extra = sorted(ours.keys() - theirs.keys())
        _fail(context, f"legal moves differ; missing={missing} extra={extra}")
    if is_checkmate(board) != oracle.is_checkmate():
        _fail(context, "checkmate status differs")
    if is_stalemate(board) != oracle.is_stalemate():
        _fail(context, "stalemate status differs")
    if has_legal_en_passant(board) != oracle.has_legal_en_passant():
        _fail(context, "en-passant availability differs")
    return ours


def compare_san(
    board: Board,
    ours: dict[str, int],
    oracle: chess.Board,
    oracle_moves: dict[str, chess.Move],
    sample: Sequence[str],
    context: str,
) -> int:
    """Compare canonical SAN and the parse round-trip for ``sample`` moves."""
    for uci in sample:
        expected = oracle.san(oracle_moves[uci])
        actual = to_san(board, ours[uci])
        if actual != expected:
            _fail(context, f"SAN for {uci}: {actual!r} != {expected!r}")
        if move_to_uci(parse_san(board, expected)) != uci:
            _fail(context, f"SAN parse for {expected!r} did not return {uci}")
    return len(sample)


def compare_games(
    games: int,
    *,
    plies: int = 160,
    seed: int = 7,
    san_sample: int = 2,
    starting_fens: Sequence[str] = (STARTING_FEN,),
    progress: bool = False,
) -> RunStats:
    """Play random games on both implementations and compare every step.

    ``san_sample`` is the number of legal moves per position whose SAN is
    compared (0 disables SAN comparison, which is what a 100k-game run wants).
    The sample is drawn deterministically from the sorted legal moves.
    """
    if games < 1:
        raise ValueError("games must be positive")
    if plies < 1:
        raise ValueError("plies must be positive")
    rng = random.Random(seed)
    positions = moves_compared = san_compared = 0
    started = time.perf_counter()

    for game_index in range(games):
        fen = starting_fens[game_index % len(starting_fens)]
        oracle = chess.Board(fen)
        board = Board(parse_fen(fen))
        for ply in range(plies):
            context = f"game {game_index} ply {ply} seed {seed} fen {oracle.fen()}"
            ours = compare_position(board, oracle, context)
            oracle_moves = {move.uci(): move for move in oracle.legal_moves}
            positions += 1
            moves_compared += len(ours)
            if san_sample and ours:
                chosen = sorted(ours)[:san_sample]
                san_compared += compare_san(board, ours, oracle, oracle_moves, chosen, context)
            if not ours:
                break
            uci = rng.choice(sorted(ours))
            board.make(ours[uci])
            oracle.push_uci(uci)
            fen_ours = to_fen(board.to_position())
            if fen_ours != oracle.fen():
                _fail(context, f"FEN after {uci}: {fen_ours!r} != {oracle.fen()!r}")
        if progress and (game_index + 1) % 1000 == 0:
            elapsed = time.perf_counter() - started
            print(f"  {game_index + 1}/{games} games, {elapsed:.0f}s", file=sys.stderr)

    return RunStats(
        games=games,
        plies=plies,
        positions=positions,
        moves_compared=moves_compared,
        san_compared=san_compared,
        seconds=time.perf_counter() - started,
    )


def compare_perft(depths: Sequence[int] = (1, 2, 3)) -> int:
    """Check every published perft position; return the number of comparisons."""
    comparisons = 0
    for name, fen in PERFT_POSITIONS:
        ours = parse_fen(fen)
        oracle = chess.Board(fen)
        for depth in depths:
            expected = _oracle_perft(oracle, depth)
            actual = perft(ours, depth)
            if actual != expected:
                _fail(f"perft {name} depth {depth}", f"{actual} != {expected}")
            comparisons += 1
    return comparisons


def compare_pgn(text: str = SAMPLE_PGN) -> None:
    """Parse one PGN with both implementations and compare the mainline."""
    import io

    import chess.pgn

    from chess_observatory.core.pgn import parse_pgn

    game = parse_pgn(text)
    oracle = chess.pgn.read_game(io.StringIO(text))
    if oracle is None:
        _fail("pgn", "the oracle could not parse the sample")
    ours = game.mainline_uci()
    theirs = [move.uci() for move in oracle.mainline_moves()]
    if ours != theirs:
        _fail("pgn", f"mainline {ours} != {theirs}")
    if to_fen(game.final_position()) != oracle.end().board().fen():
        _fail("pgn", "final position differs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the rules core against python-chess.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--games", type=int, default=2000, help="random games to play")
    parser.add_argument("--plies", type=int, default=160, help="maximum plies per game")
    parser.add_argument("--seed", type=int, default=7, help="random seed")
    parser.add_argument(
        "--san-sample",
        type=int,
        default=2,
        help="legal moves per position whose SAN is compared (0 disables)",
    )
    parser.add_argument(
        "--perft-depth",
        type=int,
        default=3,
        help="perft depth for every published position (0 skips)",
    )
    parser.add_argument("--no-pgn", action="store_true", help="skip the PGN comparison")
    parser.add_argument("--quiet", action="store_true", help="only print failures")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    try:
        if args.perft_depth:
            depths = tuple(range(1, args.perft_depth + 1))
            count = compare_perft(depths)
            if not args.quiet:
                print(f"perft: {count} comparisons match")
        if not args.no_pgn:
            compare_pgn()
            if not args.quiet:
                print("pgn: mainline and final position match")
        stats = compare_games(
            args.games,
            plies=args.plies,
            seed=args.seed,
            san_sample=args.san_sample,
            progress=not args.quiet and args.games >= 1000,
        )
    except DifferentialMismatch as exc:
        print(f"MISMATCH: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"random games: {stats.describe()}")
        print(f"OK in {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
