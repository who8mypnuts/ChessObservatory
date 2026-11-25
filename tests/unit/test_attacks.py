"""Attack generation, pins, checks, x-rays and SEE."""

from __future__ import annotations

import chess

from chess_observatory.core.attacks import (
    PAWN_ATTACKS,
    absolute_pins,
    attack_map,
    attackers_to,
    attackers_to_color,
    attacks_from,
    bishop_attacks,
    checkers,
    clear_attack_cache,
    in_check,
    is_square_attacked,
    king_attacks,
    knight_attacks,
    pawn_attacks,
    queen_attacks,
    rook_attacks,
    see_ge,
    see_square,
)
from chess_observatory.core.fen import parse_fen
from chess_observatory.core.moves import MoveFlags, pack_move
from chess_observatory.core.pieces import Color, PieceType
from chess_observatory.core.squares import (
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    parse_square,
    square_bb,
    square_name,
)

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_pawn_attacks_geometry() -> None:
    assert pawn_attacks(Color.WHITE, parse_square("e2")) == (
        square_bb(parse_square("d3")) | square_bb(parse_square("f3"))
    )
    assert pawn_attacks(Color.BLACK, parse_square("e7")) == (
        square_bb(parse_square("d6")) | square_bb(parse_square("f6"))
    )
    assert pawn_attacks(Color.WHITE, parse_square("a2")) == square_bb(parse_square("b3"))
    assert pawn_attacks(Color.WHITE, parse_square("h2")) == square_bb(parse_square("g3"))
    assert pawn_attacks(Color.WHITE, parse_square("a8")) == 0
    assert PAWN_ATTACKS[0][0] == square_bb(parse_square("b2"))


def test_knight_and_king_tables_match_precomputed() -> None:
    for name in ("a1", "b1", "e4", "h8", "d5"):
        square = parse_square(name)
        assert knight_attacks(square) == KNIGHT_ATTACKS[int(square)]
        assert king_attacks(square) == KING_ATTACKS[int(square)]
    assert knight_attacks(parse_square("a1")).bit_count() == 2
    assert king_attacks(parse_square("e4")).bit_count() == 8


def test_slider_attacks_respect_blockers() -> None:
    empty = 0
    a1 = parse_square("a1")
    assert bishop_attacks(a1, empty).bit_count() == 7
    assert rook_attacks(a1, empty).bit_count() == 14
    assert queen_attacks(a1, empty).bit_count() == 21

    # A blocker on a4 stops the rook but is itself attacked.
    a4 = square_bb(parse_square("a4"))
    attacks = rook_attacks(a1, a4)
    assert attacks & a4
    assert not attacks & square_bb(parse_square("a5"))
    assert attacks & square_bb(parse_square("h1"))

    # A blocker on c3 stops the bishop.
    c3 = square_bb(parse_square("c3"))
    diagonal = bishop_attacks(a1, c3)
    assert diagonal & c3
    assert not diagonal & square_bb(parse_square("d4"))


def test_attackers_to_finds_every_attacker() -> None:
    position = parse_fen("4k3/8/8/8/3p4/2P2N2/8/3QK3 w - - 0 1")
    target = parse_square("d4")
    white = attackers_to_color(position, target, Color.WHITE)
    assert white & square_bb(parse_square("d1"))  # queen down the open d-file
    assert white & square_bb(parse_square("c3"))  # pawn
    assert white & square_bb(parse_square("f3"))  # knight
    assert attackers_to_color(position, target, Color.BLACK) == 0
    assert attackers_to(position, target) == white


def test_attackers_to_occupancy_excludes_removed_piece() -> None:
    position = parse_fen("4k3/8/8/8/4p3/8/5P2/4K3 w - - 0 1")
    square = parse_square("f3")
    with_pawn = attackers_to(position, square)
    without_pawn = attackers_to(
        position, square, position.occupancy ^ square_bb(parse_square("e4"))
    )
    assert with_pawn == square_bb(parse_square("e4"))
    assert without_pawn == 0


def test_is_square_attacked_and_checkers() -> None:
    position = parse_fen("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1")
    assert is_square_attacked(position, parse_square("e8"), Color.WHITE)
    assert checkers(position, Color.BLACK) == square_bb(parse_square("e2"))
    assert in_check(position, Color.BLACK)
    assert not in_check(position, Color.WHITE)
    assert not is_square_attacked(position, parse_square("a1"), Color.WHITE)


def test_attacks_from_handles_every_piece_type() -> None:
    position = parse_fen(START)
    e2 = parse_square("e2")
    assert attacks_from(position, e2) == pawn_attacks(Color.WHITE, e2)
    b1 = parse_square("b1")
    assert attacks_from(position, b1) == KNIGHT_ATTACKS[int(b1)]
    e1 = parse_square("e1")
    assert attacks_from(position, e1) == KING_ATTACKS[int(e1)]
    assert attacks_from(position, parse_square("a4")) == 0


def test_absolute_pins_and_pin_ray() -> None:
    position = parse_fen("4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
    pins = absolute_pins(position, Color.WHITE)
    assert len(pins) == 1
    pin = pins[0]
    assert pin.color is Color.WHITE
    assert square_name(pin.square) == "e2"
    assert square_name(pin.attacker) == "e8"
    for name in ("e2", "e3", "e4", "e7", "e8"):
        assert pin.ray & square_bb(parse_square(name))
    assert not pin.ray & square_bb(parse_square("d2"))


def test_no_pin_when_attacker_is_not_a_slider() -> None:
    position = parse_fen("4n2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
    assert absolute_pins(position, Color.WHITE) == ()


def test_attack_map_reports_checks_pins_and_xrays() -> None:
    clear_attack_cache()
    position = parse_fen("4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
    report = attack_map(position)
    assert report.checkers[0] == 0
    assert report.checkers[1] == 0  # the black king on h8 is not in check
    assert len(report.pins_for(Color.WHITE)) == 1
    assert report.pin_ray(parse_square("e2")) == report.pins[0].ray
    assert report.attackers_to(parse_square("e8"), Color.WHITE)
    assert report.is_attacked(parse_square("e8"), Color.WHITE)
    assert report.is_attacked(parse_square("e8"))
    assert report.defenders_of(position, parse_square("e2")) == square_bb(parse_square("e1"))


def test_attack_map_cache_is_keyed_and_stable() -> None:
    clear_attack_cache()
    position = parse_fen(START)
    first = attack_map(position)
    second = attack_map(position)
    assert first is second
    moved = parse_fen(START.replace(" w ", " b "))
    assert attack_map(moved) is not first


def test_xray_sees_through_one_blocker() -> None:
    position = parse_fen("7k/8/8/8/4K3/8/8/R7 w - - 0 1")
    report = attack_map(position)
    assert report.xray_from(parse_square("a1"), Color.WHITE) == 0

    blocked = parse_fen("7k/8/8/8/p3K3/8/8/R7 w - - 0 1")
    blocked_report = attack_map(blocked)
    through = blocked_report.xray_from(parse_square("a1"), Color.WHITE)
    assert through & square_bb(parse_square("a5"))
    assert not through & square_bb(parse_square("a4"))


def test_discovered_check_candidates() -> None:
    position = parse_fen("4k3/8/8/8/8/8/4N3/4Q1K1 w - - 0 1")
    report = attack_map(position)
    discovered = report.discovered_for(Color.WHITE)
    assert any(square_name(item.square) == "e2" for item in discovered)
    assert any(square_name(item.slider) == "e1" for item in discovered)


def test_see_square_trades() -> None:
    equal = parse_fen("4k3/8/2p5/3p4/4P3/8/8/4K3 w - - 0 1")
    assert see_square(equal, parse_square("d5"), Color.WHITE) == 0

    free = parse_fen("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert see_square(free, parse_square("d5"), Color.WHITE) == 100

    bad = parse_fen("4k3/8/2p5/3p4/8/8/8/3QK3 w - - 0 1")
    assert see_square(bad, parse_square("d5"), Color.WHITE) < 0

    assert see_square(free, parse_square("a1"), Color.WHITE) < -(1 << 20)


def test_see_ge_scores_moves() -> None:
    position = parse_fen("4k3/8/2p5/3p4/4P3/8/8/4K3 w - - 0 1")
    capture = pack_move(parse_square("e4"), parse_square("d5"), flags=MoveFlags.CAPTURE)
    quiet = pack_move(parse_square("e1"), parse_square("f1"))
    assert see_ge(position, capture, 0)
    assert not see_ge(position, capture, 1)
    assert see_ge(position, quiet, 0)
    assert not see_ge(position, quiet, 1)


def test_see_handles_en_passant_and_promotion() -> None:
    ep_position = parse_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    ep_move = pack_move(
        parse_square("e5"),
        parse_square("d6"),
        flags=MoveFlags.CAPTURE | MoveFlags.EN_PASSANT,
    )
    assert see_ge(ep_position, ep_move, 100)

    promotion_position = parse_fen("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    promotion = pack_move(
        parse_square("b7"),
        parse_square("b8"),
        promotion=PieceType.QUEEN,
        flags=MoveFlags.PROMOTION,
    )
    assert see_ge(promotion_position, promotion, 800)


def test_attack_map_matches_python_chess() -> None:
    fens = (
        START,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    )
    for fen in fens:
        position = parse_fen(fen)
        report = attack_map(position)
        oracle = chess.Board(fen)
        for color, oracle_color in ((Color.WHITE, chess.WHITE), (Color.BLACK, chess.BLACK)):
            expected = 0
            for square in chess.SQUARES:
                if oracle.attackers(oracle_color, square):
                    expected |= 1 << square
            assert report.attacks[color.value] == expected
            for square in chess.SQUARES:
                ours = report.attackers_to(square, color)
                theirs = 0
                for attacker in oracle.attackers(oracle_color, square):
                    theirs |= 1 << attacker
                assert ours == theirs, (fen, color, square)


def test_attack_map_helper_accessors() -> None:
    position = parse_fen(START)
    report = attack_map(position)
    assert report.pins_for(Color.WHITE) == ()
    assert report.pin_ray(parse_square("a1")) == 0
    assert report.safe_for(Color.WHITE) == report.safe[0]
    assert report.discovered_for(Color.WHITE) == ()
    assert report.defenders_of(position, parse_square("e4")) == 0
    assert attacks_from(position, parse_square("a4")) == 0


def test_missing_kings_are_handled_gracefully() -> None:
    position = parse_fen("8/8/8/8/8/8/8/4K3 w - - 0 1", strict=False)
    assert checkers(position, Color.BLACK) == 0
    assert absolute_pins(position, Color.BLACK) == ()
    assert attack_map(position).checkers[1] == 0


def test_see_square_refuses_own_piece() -> None:
    position = parse_fen(START)
    assert see_square(position, parse_square("e2"), Color.WHITE) < -(1 << 20)


def test_attack_cache_evicts_old_entries(monkeypatch) -> None:
    from chess_observatory.core import attacks

    monkeypatch.setattr(attacks, "MAX_CACHED_MAPS", 1)
    clear_attack_cache()
    first = parse_fen(START)
    second = parse_fen(START.replace(" w ", " b "))
    attack_map(first)
    attack_map(second)
    assert len(attacks._MAP_CACHE) == 1


def test_relative_pin_shields_a_more_valuable_piece() -> None:
    from chess_observatory.core.attacks import relative_pins

    position = parse_fen("4k2r/8/8/8/8/8/7R/4K2Q w - - 0 1")
    pins = relative_pins(position, Color.WHITE)
    assert [pin.square for pin in pins] == [parse_square("h2")]
    pin = pins[0]
    assert pin.attacker == parse_square("h8")
    assert pin.ray & square_bb(parse_square("h1"))
    assert pin.ray & square_bb(parse_square("h8"))
    assert relative_pins(position, Color.BLACK) == ()
    report = attack_map(position)
    assert report.pins_for(Color.WHITE) == ()
    assert report.relative_pins_for(Color.WHITE) == (pin,)
    assert report.relative_pin_ray(parse_square("h2")) == pin.ray
    assert report.relative_pin_ray(parse_square("a1")) == 0


def test_equal_value_pieces_are_not_a_relative_pin() -> None:
    from chess_observatory.core.attacks import relative_pins

    position = parse_fen("4k2r/8/8/8/8/8/7R/4K2R w - - 0 1")
    assert relative_pins(position, Color.WHITE) == ()


def test_absolute_pins_are_not_repeated_as_relative_pins() -> None:
    from chess_observatory.core.attacks import relative_pins

    position = parse_fen("4k2r/8/8/8/8/8/7R/7K w - - 0 1")
    assert [pin.square for pin in absolute_pins(position, Color.WHITE)] == [parse_square("h2")]
    assert relative_pins(position, Color.WHITE) == ()


def test_relative_pin_through_a_knight() -> None:
    from chess_observatory.core.attacks import relative_pins

    position = parse_fen("4k3/8/b7/1N6/2Q5/8/8/4K3 w - - 0 1")
    pins = relative_pins(position, Color.WHITE)
    assert [pin.square for pin in pins] == [parse_square("b5")]
    assert pins[0].attacker == parse_square("a6")
