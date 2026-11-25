"""Property tests for the rules-core invariants (plan Phase 1, step 5).

Random legal games are generated from a hypothesis-supplied sequence of move
indices. Every step asserts the three invariants that are easy to break and
expensive to debug later:

* the incremental Zobrist key equals a full recompute;
* make followed by unmake restores the exact position and key;
* canonical FEN and SAN survive a round-trip.
"""

from __future__ import annotations

import chess
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from chess_observatory.core.fen import parse_fen, to_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, has_legal_en_passant
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.san import parse_san, to_san
from chess_observatory.core.zobrist import compute_key

pytestmark = pytest.mark.property

INDICES = st.lists(st.integers(min_value=0, max_value=10_000), max_size=60)


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(indices=INDICES)
def test_make_unmake_key_and_fen_roundtrip(indices: list[int]) -> None:
    board = Board(parse_fen(chess.STARTING_FEN))
    for index in indices:
        before = board.to_position()
        before_key = board.key
        moves = generate_legal(board)
        if not moves:
            break
        move = moves[index % len(moves)]
        board.make(move)
        after = board.to_position()
        assert board.key == compute_key(after)
        text = to_fen(after)
        canonical = parse_fen(text)
        # FEN emission drops an en-passant square nobody can capture on; that is
        # the one field where the canonical text is deliberately not the input.
        assert canonical == (after if has_legal_en_passant(after) else after.copy(ep=None))
        assert to_fen(canonical) == text
        board.unmake()
        assert board.to_position() == before
        assert board.key == before_key


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(indices=INDICES)
def test_san_roundtrips_for_every_legal_move(indices: list[int]) -> None:
    board = Board(parse_fen(chess.STARTING_FEN))
    for ply, index in enumerate(indices):
        moves = generate_legal(board)
        if not moves:
            break
        if ply % 10 == 0:
            for move in moves:
                san = to_san(board, move)
                assert move_to_uci(parse_san(board, san)) == move_to_uci(move)
        board.make(moves[index % len(moves)])
