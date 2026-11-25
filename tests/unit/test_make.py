"""Incremental make/unmake, undo records and Zobrist maintenance."""

from __future__ import annotations

import random

import chess
import pytest

from chess_observatory.core.fen import parse_fen, to_fen
from chess_observatory.core.make import Board
from chess_observatory.core.movegen import generate_legal, legal_move_from_uci
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.pieces import (
    BLACK_PAWN,
    WHITE_PAWN,
    WHITE_QUEEN,
    Color,
)
from chess_observatory.core.position import (
    CASTLE_BLACK_KING,
    CASTLE_BLACK_QUEEN,
    CASTLE_WHITE_KING,
    CASTLE_WHITE_QUEEN,
)
from chess_observatory.core.squares import parse_square
from chess_observatory.core.zobrist import compute_key
from chess_observatory.errors import IllegalMoveError


def board_for(fen: str, *, validate: bool = False) -> Board:
    return Board(parse_fen(fen), validate=validate)


def test_make_and_unmake_restore_position_and_key() -> None:
    start = parse_fen(chess.STARTING_FEN)
    board = Board(start, validate=True)
    original_key = board.key
    for move in generate_legal(board):
        before = board.to_position()
        board.make(move)
        assert board.key == compute_key(board.to_position())
        board.unmake()
        assert board.to_position() == before
        assert board.key == original_key
    assert board.undo_depth == 0


def test_unmake_returns_the_move_and_empties_the_stack() -> None:
    board = board_for(chess.STARTING_FEN)
    move = legal_move_from_uci(board, "e2e4")
    board.make(move)
    assert board.unmake() == move
    with pytest.raises(IllegalMoveError):
        board.unmake()


def test_making_a_move_from_an_empty_square_fails() -> None:
    board = board_for(chess.STARTING_FEN)
    with pytest.raises(IllegalMoveError):
        board.make(legal_move_from_uci(board, "e4e5"))


def test_castling_moves_rook_and_clears_rights() -> None:
    board = board_for("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", validate=True)
    board.make(legal_move_from_uci(board, "e1g1"))
    assert board.piece_at(parse_square("g1")) == 6
    assert board.piece_at(parse_square("f1")) == 4
    assert board.piece_at(parse_square("h1")) == 0
    assert board.castling == CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN
    board.unmake()
    assert to_fen(board.to_position()) == "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"

    board.make(legal_move_from_uci(board, "e1c1"))
    assert board.piece_at(parse_square("c1")) == 6
    assert board.piece_at(parse_square("d1")) == 4
    assert board.piece_at(parse_square("a1")) == 0


def test_en_passant_removes_the_captured_pawn() -> None:
    board = board_for("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", validate=True)
    board.make(legal_move_from_uci(board, "e5d6"))
    assert board.piece_at(parse_square("d6")) == WHITE_PAWN
    assert board.piece_at(parse_square("d5")) == 0
    assert board.ep is None
    assert board.halfmove == 0
    board.unmake()
    assert board.piece_at(parse_square("d5")) == BLACK_PAWN
    assert board.piece_at(parse_square("e5")) == WHITE_PAWN
    assert board.ep == parse_square("d6")


def test_promotion_replaces_the_pawn() -> None:
    board = board_for("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", validate=True)
    board.make(legal_move_from_uci(board, "b7b8q"))
    assert board.piece_at(parse_square("b8")) == WHITE_QUEEN
    assert board.piece_at(parse_square("b7")) == 0
    board.unmake()
    assert board.piece_at(parse_square("b7")) == WHITE_PAWN
    assert board.piece_at(parse_square("b8")) == 0


def test_capturing_a_rook_clears_its_castling_right() -> None:
    board = board_for("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", validate=True)
    board.make(legal_move_from_uci(board, "a1a8"))
    assert board.castling == CASTLE_WHITE_KING | CASTLE_BLACK_KING
    board.unmake()
    assert board.castling == (
        CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN | CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN
    )


def test_double_push_sets_en_passant_and_clock() -> None:
    board = board_for(chess.STARTING_FEN, validate=True)
    board.make(legal_move_from_uci(board, "e2e4"))
    assert board.ep == parse_square("e3")
    assert board.halfmove == 0
    assert board.fullmove == 1
    assert board.side is Color.BLACK

    board.make(legal_move_from_uci(board, "e7e5"))
    assert board.ep == parse_square("e6")
    assert board.halfmove == 0
    assert board.fullmove == 2
    assert board.side is Color.WHITE


def test_copy_is_independent() -> None:
    board = board_for(chess.STARTING_FEN)
    clone = board.copy()
    board.make(legal_move_from_uci(board, "e2e4"))
    assert clone.to_position() != board.to_position()
    assert clone.key != board.key


def test_random_games_match_python_chess_and_unwind_cleanly() -> None:
    rng = random.Random(20261123)
    for _ in range(40):
        oracle = chess.Board()
        board = Board(parse_fen(oracle.fen()), validate=True)
        initial = board.to_position()
        for _ply in range(120):
            ours = {move_to_uci(move) for move in generate_legal(board)}
            theirs = {move.uci() for move in oracle.legal_moves}
            assert ours == theirs
            if not theirs:
                break
            uci = rng.choice(sorted(theirs))
            move = next(move for move in generate_legal(board) if move_to_uci(move) == uci)
            board.make(move)
            oracle.push_uci(uci)
            assert to_fen(board.to_position()) == oracle.fen()
            assert board.key == compute_key(board.to_position())
        while board.undo_depth:
            board.unmake()
        assert board.to_position() == initial
        assert board.key == compute_key(initial)


def test_is_empty_and_missing_king() -> None:
    board = board_for(chess.STARTING_FEN)
    assert board.is_empty(parse_square("e4"))
    assert not board.is_empty(parse_square("e2"))
    kingless = Board(parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False))
    assert kingless.king_square(Color.BLACK) is None


def test_remove_piece_from_empty_square_fails() -> None:
    board = board_for(chess.STARTING_FEN)
    with pytest.raises(IllegalMoveError):
        board._remove_piece(parse_square("e4"))


def test_make_from_an_empty_square_fails() -> None:
    from chess_observatory.core.moves import pack_move

    board = board_for(chess.STARTING_FEN)
    with pytest.raises(IllegalMoveError):
        board.make(pack_move(parse_square("e4"), parse_square("e5")))


def test_validate_catches_mailbox_drift_and_key_drift() -> None:
    board = board_for(chess.STARTING_FEN, validate=True)
    move = legal_move_from_uci(board, "e2e4")
    board.mailbox[0] = 1  # corrupt the mailbox behind the bitboards
    with pytest.raises(AssertionError, match="mailbox"):
        board.make(move)

    clean = board_for(chess.STARTING_FEN, validate=True)
    clean.key ^= 1
    with pytest.raises(AssertionError, match="incremental key"):
        clean.make(legal_move_from_uci(clean, "e2e4"))
