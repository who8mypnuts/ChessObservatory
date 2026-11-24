"""Shared test fixtures and factories (plan Phase 0, step 9).

``python-chess`` is a test-only oracle. It is imported here, never from
``src/``; the import-graph guard enforces that.
"""

from __future__ import annotations

import io
import os
from collections.abc import Callable

import chess
import chess.pgn
import pytest

# Qt must be told to run headless before any PySide6 import happens.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PosFactory = Callable[..., chess.Board]
GameFactory = Callable[[str], chess.pgn.Game]


@pytest.fixture
def pos() -> PosFactory:
    """Build a board: ``pos()`` or ``pos(fen)``."""

    def make(fen: str = chess.STARTING_FEN) -> chess.Board:
        return chess.Board(fen)

    return make


@pytest.fixture
def game() -> GameFactory:
    """Parse a PGN string into a game tree."""

    def make(pgn: str) -> chess.pgn.Game:
        parsed = chess.pgn.read_game(io.StringIO(pgn))
        if parsed is None:
            raise ValueError("not a PGN")
        return parsed

    return make
