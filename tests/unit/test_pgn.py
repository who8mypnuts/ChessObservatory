"""PGN headers, comments, NAGs, variations, annotations and streaming."""

from __future__ import annotations

import io

import chess
import chess.pgn
import pytest

from chess_observatory.core.pgn import (
    PgnGame,
    emit_pgn,
    iter_pgn,
    parse_pgn,
    parse_pgn_games,
    read_pgn,
    write_pgn,
)
from chess_observatory.errors import InvalidPgnError

SAMPLE = """[Event "Test Match"]
[Site "Local"]
[Date "2026.11.23"]
[Round "1"]
[White "Alpha"]
[Black "Beta"]
[Result "1-0"]
[WhiteElo "2000"]

{Opening study} 1. e4 {[%clk 0:04:55]} e5 {[%eval 0.25]} 2. Nf3 Nc6
3. Bb5 {Spanish} $1 a6 (3... Nf6 4. O-O (4. d3 Be7)) 4. Ba4 1-0
"""


def test_headers_and_result() -> None:
    game = parse_pgn(SAMPLE)
    assert game.headers["Event"] == "Test Match"
    assert game.headers["White"] == "Alpha"
    assert game.headers["WhiteElo"] == "2000"
    assert game.result == "1-0"


def test_mainline_moves() -> None:
    game = parse_pgn(SAMPLE)
    assert game.mainline_uci() == ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4"]
    assert game.comment == "Opening study"


def test_comments_nags_clock_and_eval() -> None:
    game = parse_pgn(SAMPLE)
    e4, e5, _nf3, _nc6, bb5, _a6, _ba4 = game.moves
    assert e4.clock == 295
    assert e4.comment is None
    assert e5.eval_cp == 25
    assert bb5.comment == "Spanish"
    assert bb5.nags == (1,)


def test_variations_are_attached_to_the_replaced_move() -> None:
    game = parse_pgn(SAMPLE)
    a6 = game.moves[5]
    assert len(a6.variations) == 1
    variation = a6.variations[0]
    assert [node.san for node in variation] == ["Nf6", "O-O"]
    nested = variation[1].variations
    assert len(nested) == 1
    assert [node.san for node in nested[0]] == ["d3", "Be7"]


def test_final_position_matches_python_chess() -> None:
    game = parse_pgn(SAMPLE)
    oracle = chess.pgn.read_game(io.StringIO(SAMPLE))
    assert oracle is not None
    expected = [move.uci() for move in oracle.mainline_moves()]
    assert game.mainline_uci() == expected
    oracle_board = chess.Board()
    for move in oracle.mainline_moves():
        oracle_board.push(move)
    from chess_observatory.core.fen import to_fen

    assert to_fen(game.final_position()) == oracle_board.fen()


def test_roundtrip_preserves_structure() -> None:
    game = parse_pgn(SAMPLE)
    text = emit_pgn(game)
    again = parse_pgn(text)
    assert again.headers == game.headers
    assert again.result == game.result
    assert again.mainline_uci() == game.mainline_uci()
    assert again.moves[4].nags == (1,)
    assert again.moves[4].comment == "Spanish"
    assert again.moves[0].clock == 295
    assert again.moves[1].eval_cp == 25
    assert len(again.moves[5].variations) == 1
    assert [node.san for node in again.moves[5].variations[0]] == ["Nf6", "O-O"]


def test_emitted_lines_respect_width() -> None:
    game = parse_pgn(SAMPLE)
    text = emit_pgn(game, line_width=40)
    movetext = text.split("\n\n", 1)[1]
    for line in movetext.splitlines():
        assert len(line) <= 40, line


def test_parse_multiple_games() -> None:
    second = """[Event "Second"]
[Result "0-1"]

1. d4 d5 0-1
"""
    games = parse_pgn_games(SAMPLE + "\n" + second)
    assert len(games) == 2
    assert games[1].headers["Event"] == "Second"
    assert games[1].result == "0-1"
    assert games[1].mainline_uci() == ["d2d4", "d7d5"]


def test_streaming_reader_yields_games() -> None:
    second = """[Event "Second"]
[Result "0-1"]

1. d4 d5 0-1
"""
    games = list(iter_pgn((SAMPLE + "\n" + second).splitlines(keepends=True)))
    assert [game.headers["Event"] for game in games] == ["Test Match", "Second"]

    encoded = list(iter_pgn(line.encode("utf-8") for line in (SAMPLE + "\n" + second).splitlines()))
    assert len(encoded) == 2


def test_read_pgn_accepts_text_bytes_and_streams() -> None:
    assert len(read_pgn(SAMPLE)) == 1
    assert len(read_pgn(SAMPLE.encode("utf-8"))) == 1
    assert len(read_pgn(SAMPLE.splitlines(keepends=True))) == 1


def test_latin1_fallback_for_legacy_files() -> None:
    text = '[White "Jos\u00e9"]\n[Result "1-0"]\n\n1. e4 1-0\n'
    raw = text.encode("latin-1")
    game = read_pgn(raw, encoding="utf-8")[0]
    assert game.headers["White"] == "Jos\u00e9"


def test_headerless_pgn_is_accepted() -> None:
    game = parse_pgn("1. e4 e5 2. Nf3 *")
    assert game.headers["Result"] == "*"
    assert game.mainline_uci() == ["e2e4", "e7e5", "g1f3"]


def test_fen_header_sets_the_start_position() -> None:
    text = """[SetUp "1"]
[FEN "4k3/8/8/8/8/8/8/4K3 w - - 0 1"]
[Result "*"]

1. Kd1 *
"""
    game = parse_pgn(text)
    assert game.start_position().mailbox.count(0) == 62
    assert game.mainline_uci() == ["e1d1"]


def test_writer_roundtrip() -> None:
    games = [parse_pgn(SAMPLE), parse_pgn('[Event "B"]\n[Result "*"]\n\n1. c4 *\n')]
    stream = io.StringIO()
    write_pgn(games, stream)
    reparsed = parse_pgn_games(stream.getvalue())
    assert [game.headers["Event"] for game in reparsed] == ["Test Match", "B"]


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ('[Event "x"]\n\n1. e4 {unterminated', "unterminated comment"),
        ('[Event "x"]\n\n1. e4 (1. d4', "unterminated variation"),
        ('[Event "x"]\n\n1. e4 )', "unbalanced"),
        ('[Event "x"]\n\n1. e9', "cannot play"),
        ('[Event "x"]\n\n1. e4 --', "null moves"),
        ('[Event "x"]\n[FEN "bad"]\n\n1. e4 *', "not a valid FEN"),
    ],
)
def test_errors_are_precise(text: str, fragment: str) -> None:
    with pytest.raises(InvalidPgnError) as excinfo:
        parse_pgn(text)
    assert fragment.lower() in str(excinfo.value).lower()


def test_empty_pgn_is_rejected() -> None:
    with pytest.raises(InvalidPgnError):
        parse_pgn("   \n\n")


def test_pgn_game_helpers() -> None:
    game = parse_pgn(SAMPLE)
    assert isinstance(game, PgnGame)
    assert game.header("White") == "Alpha"
    assert game.header("Missing", "fallback") == "fallback"
    assert game.mainline_moves() == [node.move for node in game.moves]


def test_header_escapes_are_unescaped() -> None:
    text = '[Event "A \\"quote\\" and \\\\ slash"]\n[Result "*"]\n\n1. e4 *\n'
    game = parse_pgn(text)
    assert game.headers["Event"] == 'A "quote" and \\ slash'


def test_semicolon_comments_are_ignored() -> None:
    game = parse_pgn('[Event "x"]\n[Result "*"]\n\n1. e4 ; rest of the line\ne5 *\n')
    assert game.mainline_uci() == ["e2e4", "e7e5"]


def test_bracket_annotations_outside_braces() -> None:
    game = parse_pgn('[Event "x"]\n[Result "*"]\n\n1. e4 [%clk 0:01:30] e5 *\n')
    assert game.moves[0].clock == 90


def test_symbolic_annotations_become_nags() -> None:
    game = parse_pgn('[Event "x"]\n[Result "*"]\n\n1. e4!? e5 *\n')
    assert game.moves[0].nags == (5,)


def test_eval_mate_annotations_roundtrip() -> None:
    game = parse_pgn('[Event "x"]\n[Result "*"]\n\n1. e4 {[%eval #3]} e5 {[%eval -#2]} *\n')
    assert game.moves[0].eval_mate == 3
    assert game.moves[1].eval_mate == -2
    text = emit_pgn(game)
    assert "[%eval #3]" in text
    assert "[%eval -#2]" in text
    again = parse_pgn(text)
    assert again.moves[0].eval_mate == 3
    assert again.moves[1].eval_mate == -2


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ('[Event "x"]\n[Result "*"]\n\n1. e4 {[%clk abc]} *\n', "invalid clock"),
        ('[Event "x"]\n[Result "*"]\n\n1. e4 {[%eval foo]} *\n', "invalid evaluation"),
        ('[Event "x"]\n[Result "*"]\n\n1. e4 $ *\n', "nag marker"),
        ('[Event "x"]\n[Result "*"]\n\n(1. e4) *\n', "variation without"),
    ],
)
def test_more_pgn_errors(text: str, fragment: str) -> None:
    with pytest.raises(InvalidPgnError) as excinfo:
        parse_pgn(text)
    assert fragment.lower() in str(excinfo.value).lower()


def test_variation_may_start_with_a_comment() -> None:
    game = parse_pgn('[Event "x"]\n[Result "*"]\n\n1. e4 e5 ({variation} 1... c5) *\n')
    assert game.moves[1].variations[0][0].san == "c5"


def test_header_like_line_inside_a_comment_does_not_split_games() -> None:
    text = """[Event "A"]
[Result "*"]

1. e4 {multi
[Event "not a header"]
line} e5 *
"""
    games = parse_pgn_games(text)
    assert len(games) == 1
    assert games[0].headers["Event"] == "A"


def test_iter_pgn_ignores_blank_streams() -> None:
    assert list(iter_pgn(["\n", "   \n"])) == []


def test_emit_adds_setup_and_default_result() -> None:
    game = PgnGame(headers={"FEN": "4k3/8/8/8/8/8/8/4K3 w - - 0 1"})
    text = emit_pgn(game)
    assert '[SetUp "1"]' in text
    assert '[Result "*"]' in text
    again = parse_pgn(text)
    assert again.headers["SetUp"] == "1"
    assert again.result == "*"


def test_start_position_reports_a_bad_fen() -> None:
    game = PgnGame(headers={"FEN": "bad"})
    with pytest.raises(InvalidPgnError):
        game.start_position()


def test_to_pgn_method() -> None:
    game = parse_pgn(SAMPLE)
    assert '[Event "Test Match"]' in game.to_pgn()
