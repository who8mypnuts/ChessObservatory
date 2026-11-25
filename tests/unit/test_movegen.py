"""Legal move generation, perft and terminal states."""

from __future__ import annotations

import random

import chess
import pytest

from chess_observatory.core.attacks import in_check
from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import (
    find_legal,
    generate_legal,
    generate_pseudo_legal,
    has_legal_en_passant,
    is_checkmate,
    is_game_over,
    is_legal,
    is_stalemate,
    legal_move_from_uci,
    perft,
    perft_divide,
)
from chess_observatory.core.moves import MoveFlags, move_flags, move_to_uci
from chess_observatory.core.pieces import Color

STANDARD_POSITIONS: dict[str, tuple[str, tuple[int, ...]]] = {
    "start": (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        (20, 400, 8902, 197281, 4865609, 119060324),
    ),
    "kiwipete": (
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        (48, 2039, 97862, 4085603, 193690690),
    ),
    "position-3": (
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        (14, 191, 2812, 43238, 674624),
    ),
    "position-4": (
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        (6, 264, 9467, 422333, 15833292),
    ),
    "position-5": (
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        (44, 1486, 62379, 2103487, 89941194),
    ),
    "position-6": (
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        (46, 2079, 89890, 3894594, 164075551),
    ),
}

FAST_CASES = [
    (name, fen, depth, expected[depth - 1])
    for name, (fen, expected) in STANDARD_POSITIONS.items()
    for depth in (1, 2, 3)
]

SLOW_CASES = [
    ("start-4", STANDARD_POSITIONS["start"][0], 4, 197281),
    ("start-5", STANDARD_POSITIONS["start"][0], 5, 4865609),
    ("kiwipete-4", STANDARD_POSITIONS["kiwipete"][0], 4, 4085603),
    ("position-3-4", STANDARD_POSITIONS["position-3"][0], 4, 43238),
    ("position-4-4", STANDARD_POSITIONS["position-4"][0], 4, 422333),
    ("position-5-4", STANDARD_POSITIONS["position-5"][0], 4, 2103487),
    ("position-6-4", STANDARD_POSITIONS["position-6"][0], 4, 3894594),
]


@pytest.mark.parametrize(
    ("name", "fen", "depth", "expected"), FAST_CASES, ids=[c[0] for c in FAST_CASES]
)
def test_perft_standard_positions(name: str, fen: str, depth: int, expected: int) -> None:
    assert perft(parse_fen(fen), depth) == expected, name


@pytest.mark.slow
@pytest.mark.parametrize(
    ("name", "fen", "depth", "expected"), SLOW_CASES, ids=[c[0] for c in SLOW_CASES]
)
def test_perft_standard_positions_slow(name: str, fen: str, depth: int, expected: int) -> None:
    assert perft(parse_fen(fen), depth) == expected, name


def test_perft_zero_and_divide() -> None:
    position = parse_fen(chess.STARTING_FEN)
    assert perft(position, 0) == 1
    divide = perft_divide(position, 1)
    assert len(divide) == 20
    assert sum(divide.values()) == 20
    assert divide["e2e4"] == 1
    assert perft_divide(position, 0) == {"": 1}


def test_starting_moves_are_the_twenty_known_ones() -> None:
    moves = generate_legal(parse_fen(chess.STARTING_FEN))
    assert {move_to_uci(move) for move in moves} == {
        "a2a3",
        "a2a4",
        "b2b3",
        "b2b4",
        "c2c3",
        "c2c4",
        "d2d3",
        "d2d4",
        "e2e3",
        "e2e4",
        "f2f3",
        "f2f4",
        "g2g3",
        "g2g4",
        "h2h3",
        "h2h4",
        "b1a3",
        "b1c3",
        "g1f3",
        "g1h3",
    }
    assert len(generate_pseudo_legal(parse_fen(chess.STARTING_FEN))) == 20


def test_castling_requires_rights_empty_path_and_safe_squares() -> None:
    # White may castle both ways.
    both = parse_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    uci = {move_to_uci(move) for move in generate_legal(both)}
    assert "e1g1" in uci and "e1c1" in uci

    # No rights.
    none = parse_fen("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
    assert "e1g1" not in {move_to_uci(move) for move in generate_legal(none)}

    # Blocked path.
    blocked = parse_fen("r3k2r/8/8/8/8/8/8/R2BK2R w KQkq - 0 1")
    assert "e1c1" not in {move_to_uci(move) for move in generate_legal(blocked)}

    # Through an attacked square: black rook f8 attacks f1.
    attacked = parse_fen("1k3r2/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert "e1g1" not in {move_to_uci(move) for move in generate_legal(attacked)}

    # Out of check.
    checked = parse_fen("1k2r3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert "e1g1" not in {move_to_uci(move) for move in generate_legal(checked)}


def test_en_passant_capture_is_generated_and_can_be_pinned() -> None:
    free = parse_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    ep_move = legal_move_from_uci(free, "e5d6")
    assert move_flags(ep_move) & MoveFlags.EN_PASSANT
    assert has_legal_en_passant(free)

    # The e-file pin makes the en-passant capture illegal.
    pinned = parse_fen("4r2k/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    assert "e5d6" not in {move_to_uci(move) for move in generate_legal(pinned)}
    assert not has_legal_en_passant(pinned)
    assert not is_legal(pinned, ep_move)


def test_promotions_generate_four_choices() -> None:
    position = parse_fen("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    promotions = [
        move for move in generate_legal(position) if move_flags(move) & MoveFlags.PROMOTION
    ]
    assert {move_to_uci(move) for move in promotions} == {
        "b7b8n",
        "b7b8b",
        "b7b8r",
        "b7b8q",
    }
    assert all(move_flags(move) & MoveFlags.PROMOTION for move in promotions)


def test_double_check_allows_king_moves_only() -> None:
    # Rook e8 and bishop b5 both check the white king on e2.
    position = parse_fen("4r2k/8/8/1b6/8/8/4K3/8 w - - 0 1")
    moves = generate_legal(position)
    assert all(move_to_uci(move)[:2] == "e2" for move in moves)
    assert moves


def test_check_evasions_are_captures_or_blocks() -> None:
    position = parse_fen("4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
    # The white rook is pinned, so it may only move along the e-file.
    moves = {move_to_uci(move) for move in generate_legal(position)}
    assert "e2e8" in moves
    assert "e2e3" in moves
    assert "e2d2" not in moves


def test_terminal_states() -> None:
    mate = parse_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    assert is_checkmate(mate)
    assert is_game_over(mate)
    assert not is_stalemate(mate)

    stalemate = parse_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert is_stalemate(stalemate)
    assert is_game_over(stalemate)
    assert not is_checkmate(stalemate)

    alive = parse_fen(chess.STARTING_FEN)
    assert not is_game_over(alive)


def test_find_legal_adds_flags_to_uci_moves() -> None:
    position = parse_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    raw = legal_move_from_uci(position, "e5d6")
    found = find_legal(position, raw)
    assert found == raw
    assert find_legal(position, raw) is not None


def test_legal_moves_match_python_chess_over_random_games() -> None:
    rng = random.Random(424242)
    for _ in range(30):
        oracle = chess.Board()
        board = Board(parse_fen(oracle.fen()))
        for _ply in range(150):
            ours = {move_to_uci(move) for move in generate_legal(board)}
            theirs = {move.uci() for move in oracle.legal_moves}
            assert ours == theirs
            assert is_checkmate(board) == oracle.is_checkmate()
            assert is_stalemate(board) == oracle.is_stalemate()
            assert has_legal_en_passant(board) == oracle.has_legal_en_passant()
            if not theirs:
                break
            uci = rng.choice(sorted(theirs))
            board.make(legal_move_from_uci(board, uci))
            oracle.push_uci(uci)
        assert in_check(board, Color.WHITE) == oracle.is_attacked_by(
            chess.BLACK, oracle.king(chess.WHITE)
        )
        assert in_check(board, Color.BLACK) == oracle.is_attacked_by(
            chess.WHITE, oracle.king(chess.BLACK)
        )


def test_pseudo_legal_generator_includes_captures_and_en_passant() -> None:
    capture = parse_fen("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    uci = {move_to_uci(move) for move in generate_pseudo_legal(capture)}
    assert "e4d5" in uci

    ep = parse_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    ep_move = next(move for move in generate_pseudo_legal(ep) if move_to_uci(move) == "e5d6")
    assert move_flags(ep_move) & MoveFlags.EN_PASSANT


def test_position_without_a_king_falls_back_to_pseudo_legal() -> None:
    position = parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False)
    assert len(generate_legal(position)) == len(generate_pseudo_legal(position))


def test_malformed_en_passant_is_ignored_safely() -> None:
    position = parse_fen("4k3/8/8/4P3/8/8/8/4K3 w - d6 0 1", strict=False)
    moves = {move_to_uci(move) for move in generate_legal(position)}
    assert "e5d6" not in moves
