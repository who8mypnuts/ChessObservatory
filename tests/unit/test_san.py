"""SAN generation, disambiguation and tolerant parsing."""

from __future__ import annotations

import random

import chess
import pytest

from chess_observatory.core.fen import parse_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, legal_move_from_uci
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.san import parse_san, san_roundtrip, to_san
from chess_observatory.errors import IllegalMoveError, InvalidSanError


def san_for(fen: str, uci: str) -> str:
    position = parse_fen(fen)
    return to_san(position, legal_move_from_uci(position, uci))


def test_basic_piece_and_pawn_moves() -> None:
    start = chess.STARTING_FEN
    assert san_for(start, "e2e4") == "e4"
    assert san_for(start, "g1f3") == "Nf3"
    assert san_for(start, "b1c3") == "Nc3"


def test_castling_uses_letter_o() -> None:
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    assert san_for(fen, "e1g1") == "O-O"
    assert san_for(fen, "e1c1") == "O-O-O"
    black = "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1"
    assert san_for(black, "e8g8") == "O-O"
    assert san_for(black, "e8c8") == "O-O-O"


def test_captures_promotions_and_en_passant() -> None:
    assert san_for("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", "e4d5") == "exd5"
    assert san_for("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8q") == "b8=Q+"
    assert san_for("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8n") == "b8=N"
    assert san_for("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6") == "exd6"
    assert san_for("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", "e4e5") == "e5"


def test_check_and_mate_suffixes() -> None:
    assert san_for("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8") == "Ra8+"
    assert san_for("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1", "a1a8") == "Ra8#"
    assert san_for("7k/5K2/6Q1/8/8/8/8/8 w - - 0 1", "g6g7") == "Qg7#"


def test_minimal_disambiguation() -> None:
    two_files = "4k3/8/8/8/8/2N5/8/4K1N1 w - - 0 1"
    assert san_for(two_files, "c3e2") == "Nce2"
    assert san_for(two_files, "g1e2") == "Nge2"

    same_file = "4k3/8/2N5/8/8/8/2N5/4K3 w - - 0 1"
    assert san_for(same_file, "c2d4") == "N2d4"
    assert san_for(same_file, "c6d4") == "N6d4"


def test_capture_disambiguation_comes_before_x() -> None:
    fen = "4k3/8/8/8/8/2N5/4p3/4K1N1 w - - 0 1"
    assert san_for(fen, "c3e2") == "Ncxe2"
    assert san_for(fen, "g1e2") == "Ngxe2"


def test_parse_canonical_and_tolerant_forms() -> None:
    start = parse_fen(chess.STARTING_FEN)
    assert move_to_uci(parse_san(start, "e4")) == "e2e4"
    assert move_to_uci(parse_san(start, "Nf3")) == "g1f3"
    assert move_to_uci(parse_san(start, "Nf3+")) == "g1f3"
    assert move_to_uci(parse_san(start, "Nf3!?")) == "g1f3"

    castle = parse_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert move_to_uci(parse_san(castle, "O-O")) == "e1g1"
    assert move_to_uci(parse_san(castle, "0-0-0")) == "e1c1"

    promotion = parse_fen("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    assert move_to_uci(parse_san(promotion, "b8=Q")) == "b7b8q"
    assert move_to_uci(parse_san(promotion, "b8Q")) == "b7b8q"
    assert move_to_uci(parse_san(promotion, "b8=N+")) == "b7b8n"


def test_parse_en_passant_and_missing_capture_marker() -> None:
    position = parse_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    assert move_to_uci(parse_san(position, "exd6")) == "e5d6"
    assert move_to_uci(parse_san(position, "exd6 e.p.")) == "e5d6"

    # Tolerant fallback: the capture marker is missing but the move is unique.
    quiet_capture = parse_fen("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert move_to_uci(parse_san(quiet_capture, "ed5")) == "e4d5"


def test_parse_rejects_illegal_ambiguous_and_empty() -> None:
    start = parse_fen(chess.STARTING_FEN)
    with pytest.raises(InvalidSanError):
        parse_san(start, "")
    with pytest.raises(InvalidSanError):
        parse_san(start, "e5")
    with pytest.raises(InvalidSanError):
        parse_san(start, "Ke2")
    with pytest.raises(InvalidSanError):
        parse_san(start, "O-O")

    ambiguous = parse_fen("4k3/8/8/8/8/2N5/8/4K1N1 w - - 0 1")
    with pytest.raises(InvalidSanError):
        parse_san(ambiguous, "Ne2")


def test_to_san_rejects_illegal_moves() -> None:
    start = parse_fen(chess.STARTING_FEN)
    with pytest.raises(IllegalMoveError):
        to_san(start, 0)


def _san_differential(games: int, plies: int) -> None:
    rng = random.Random(777)
    for _ in range(games):
        oracle = chess.Board()
        board = Board(parse_fen(oracle.fen()))
        for _ply in range(plies):
            legal = generate_legal(board)
            ours = {move_to_uci(move): move for move in legal}
            theirs = {move.uci(): move for move in oracle.legal_moves}
            assert ours.keys() == theirs.keys()
            for uci, move in ours.items():
                expected = oracle.san(theirs[uci])
                assert to_san(board, move) == expected, (oracle.fen(), uci)
                assert san_roundtrip(board, move) == move
                assert move_to_uci(parse_san(board, expected)) == uci
            if not theirs:
                break
            uci = rng.choice(sorted(theirs))
            board.make(ours[uci])
            oracle.push_uci(uci)


def test_san_roundtrip_on_every_move_of_random_games() -> None:
    _san_differential(games=3, plies=60)


@pytest.mark.slow
def test_san_roundtrip_slow() -> None:
    _san_differential(games=20, plies=120)


def test_full_disambiguation_when_file_and_rank_are_needed() -> None:
    fen = "4k3/8/8/8/8/Q7/8/Q1Q1K3 w - - 0 1"
    assert san_for(fen, "a1c3") == "Qa1c3"


@pytest.mark.parametrize(
    "text",
    ["!", "e", "Nab1c3", "Naab3", "N11c3", "Nzc3", "N2f3", "Nbf3", "Q"],
)
def test_more_malformed_san_is_rejected(text: str) -> None:
    with pytest.raises(InvalidSanError):
        parse_san(parse_fen(chess.STARTING_FEN), text)
