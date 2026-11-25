"""Strict and permissive FEN parsing, canonical emission."""

from __future__ import annotations

import chess
import pytest

from chess_observatory.core.fen import STARTING_FEN, parse_fen, to_fen
from chess_observatory.core.pieces import Color
from chess_observatory.errors import InvalidFenError

STANDARD_FENS = (
    chess.STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "4k3/8/8/8/8/8/8/4K3 w - - 42 99",
)


@pytest.mark.parametrize("fen", STANDARD_FENS)
def test_roundtrip(fen: str) -> None:
    position = parse_fen(fen)
    assert to_fen(position) == fen
    assert position.strict is True


def test_starting_fen_constant() -> None:
    assert STARTING_FEN == chess.STARTING_FEN
    assert to_fen(parse_fen(STARTING_FEN)) == chess.STARTING_FEN


def test_side_and_clocks_are_parsed() -> None:
    position = parse_fen("4k3/8/8/8/8/8/8/4K3 b - - 17 42")
    assert position.side is Color.BLACK
    assert position.halfmove == 17
    assert position.fullmove == 42


def test_en_passant_is_emitted_only_when_capturable() -> None:
    capturable = parse_fen("4k3/8/8/8/4pP2/8/8/4K3 b - f3 0 1")
    assert to_fen(capturable).split()[3] == "f3"

    ignored = parse_fen("4k3/8/8/8/p4P2/8/8/4K3 b - f3 0 1")
    assert to_fen(ignored).split()[3] == "-"


def test_permissive_mode_keeps_experimental_positions() -> None:
    position = parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False)
    assert position.strict is False
    assert position.king_square(Color.WHITE) is not None
    assert position.king_square(Color.BLACK) is None
    assert to_fen(position) == "8/8/8/8/8/8/8/4K3 w - - 0 1"


@pytest.mark.parametrize(
    ("fen", "fragment"),
    [
        ("", "field"),
        ("8/8/8/8/8/8/8/8 w - - 0", "field"),
        ("8/8/8/8/8/8/8 w - - 0 1", "rank"),
        ("8/8/8/8/8/8/8/9 w - - 0 1", "wider"),
        ("8/8/8/8/8/8/8/7 w - - 0 1", "file"),
        ("8/8/8/8/8/8/8/80 w - - 0 1", "digit 0"),
        ("8/8/8/8/8/8/8/4K2X w - - 0 1", "Unknown piece"),
        ("4k3/8/8/8/8/8/8/4K3 x - - 0 1", "Side-to-move"),
        ("4k3/8/8/8/8/8/8/4K3 w X - 0 1", "castling"),
        ("4k3/8/8/8/8/8/8/4K3 w KK - 0 1", "Duplicate"),
        ("4k3/8/8/8/8/8/8/4K3 w - z9 0 1", "en-passant"),
        ("4k3/8/8/8/8/8/8/4K3 w - e4 0 1", "rank 3 or rank 6"),
        ("4k3/8/8/8/8/8/8/4K3 w - - -1 1", "negative"),
        ("4k3/8/8/8/8/8/8/4K3 w - - x 1", "not an integer"),
        ("4k3/8/8/8/8/8/8/8 w - - 0 1", "no white king"),
        ("4k3/8/8/8/8/8/8/4KK2 w - - 0 1", "more than one white king"),
        ("4k3/8/8/8/8/8/8/P3K3 w - - 0 1", "first or eighth rank"),
        ("4k3/8/8/8/8/P7/PPPPPPPP/4K3 w - - 0 1", "more than eight pawns"),
        ("4k3/8/QQQQQQQQ/QQQQQQQQ/8/8/8/4K3 w - - 0 1", "more than sixteen"),
        ("8/8/8/8/8/8/8/4kK2 w - - 0 1", "adjacent"),
        ("4k3/8/8/8/8/8/8/5K2 w K - 0 1", "king is not on e1"),
        ("4k3/8/8/8/8/8/8/4K2R w Q - 0 1", "without a rook on a1"),
        ("4k3/8/8/8/8/8/8/4K3 w - e3 0 1", "wrong rank"),
        ("4k3/8/8/8/8/8/8/4K3 w - d6 0 1", "no pawn"),
        ("4k3/8/8/3p4/8/8/8/4K3 w - d6 1 1", "halfmove clock of 0"),
        ("4r2k/8/8/8/8/8/8/4K3 b - - 0 1", "not to move is in check"),
    ],
)
def test_strict_errors_are_precise(fen: str, fragment: str) -> None:
    with pytest.raises(InvalidFenError) as excinfo:
        parse_fen(fen)
    assert fragment.lower() in str(excinfo.value).lower()


def test_strict_error_carries_context_and_hint() -> None:
    with pytest.raises(InvalidFenError) as excinfo:
        parse_fen("8/8/8/8/8/8/8/8 w - - 0 1")
    error = excinfo.value
    assert error.code == "core.invalid_fen"
    assert error.hint is not None


@pytest.mark.parametrize(
    ("fen", "fragment"),
    [
        ("4k3/8/8/8/8/8/8/4K3 w K - 0 1", "without a rook on h1"),
        ("1k6/8/8/8/8/8/8/4K3 b k - 0 1", "king is not on e8"),
        ("4k3/8/8/8/8/8/8/4K3 b k - 0 1", "without a rook on h8"),
        ("4k3/8/8/8/8/8/8/4K3 b q - 0 1", "without a rook on a8"),
    ],
)
def test_more_castling_right_errors(fen: str, fragment: str) -> None:
    with pytest.raises(InvalidFenError) as excinfo:
        parse_fen(fen)
    assert fragment in str(excinfo.value)
