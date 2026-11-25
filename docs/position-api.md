# Position API

> **Status:** landed in Phase 1 and frozen for downstream modules. Everything
> below exists in `chess_observatory.core`, is covered by the unit and
> differential suites, and is what Phases 2+ code against. Additive changes are
> welcome; renames need an ADR.

The rules core has no runtime third-party dependencies
([ADR-0001](adr/0001-own-bitboard-rules-core.md)). `python-chess` is a
development-only oracle.

## Representation

| Type | Shape |
|------|-------|
| `Square` | `0 = a1` … `63 = h8`; a `NewType` over `int` |
| `Piece` | empty `0`; white `1..6`, black `9..14` (black bit `8`) |
| `Move` | packed 32-bit int: from `0..5`, to `6..11`, promotion `12..15`, flags `16..20` |
| `MoveList` | `array('i')` of packed moves, not a list of objects |
| `Position` | frozen slots dataclass: 12 piece bitboards, `bytes(64)` mailbox, side, castling mask, en-passant square, clocks, `strict`, `variant_note` |
| `Board` | mutable `BoardView` with an undo stack and an incrementally updated Zobrist key |

Castling bits are `WK=1`, `WQ=2`, `BK=4`, `BQ=8` (`CASTLE_*` constants in
`position.py`). The mailbox and the bitboards are redundant on purpose: fast
lookup by square, fast set operations by piece. `Position.is_consistent()`
checks that they agree.

## Positions and FEN

```python
from chess_observatory.core.fen import parse_fen, to_fen

position = parse_fen(fen)  # strict: illegal states raise
experimental = parse_fen(fen, strict=False)
text = to_fen(position)  # canonical; en passant only if capturable
```

- `parse_fen(strict=True)` raises `InvalidFenError` with a precise message for
  wrong material, missing kings, side-not-to-move in check, impossible
  castling rights and malformed fields.
- `strict=False` accepts experimental states and records what is wrong in
  `Position.variant_note` (or in the edit's `LegalityReport`).
- `to_fen` drops the en-passant field unless a legal en-passant capture exists,
  matching the oracle's normalisation, so FEN round-trips are exact.
- `Position.empty()`, `Position.from_pieces(...)`, `Position.piece_at`,
  `Position.pieces`, `Position.color_occupancy`, `Position.king_square`,
  `Position.occupancy`, `Position.copy()` (via `dataclasses.replace`) are the
  construction and inspection surface.

## Moves and generation

```python
from chess_observatory.core.movegen import generate_legal, legal_move_from_uci
from chess_observatory.core.moves import move_to_uci, pack_move

moves = generate_legal(board)  # MoveList
move = legal_move_from_uci(board, "e2e4")  # fully flagged, raises if illegal
uci = move_to_uci(move)
```

- `generate_pseudo_legal` is exposed for tests and for relaxed positions; the
  production path is `generate_legal`.
- `find_legal`, `is_legal`, `is_checkmate`, `is_stalemate`, `is_game_over`,
  `has_legal_en_passant`, `perft`, `perft_divide` live in `movegen.py`.
- Legality is computed directly: checkers, absolute-pin rays, and a
  king-danger mask for occupancy changes. En passant is simulated because it
  can expose a pin on the fifth rank.
- A move passed to `Board.make` must already carry its flags. Raw input goes
  through `legal_move_from_uci` or `find_legal` first.

## Attacks and SEE

```python
from chess_observatory.core.attacks import attack_map, attackers_to, see_ge

report = attack_map(position)  # cached by (zobrist, variant_key)
report.attackers_to(square, color)  # bitboard of attackers
report.attacks[color]  # every square colour attacks
report.checkers[color]  # checking pieces
report.pins_for(color)  # absolute pins (against the king)
report.pin_ray(square)
report.relative_pins_for(color)  # pins against a more valuable piece
report.relative_pin_ray(square)
report.discovered_for(color)  # discovered-check candidates
report.xray_from(square, color)  # x-ray through one blocker
report.safe_for(color)  # squares occupiable with SEE >= 0
```

`attackers_to`, `absolute_pins`, `relative_pins`, `attack_map`, `see_ge`,
`see_square` and `clear_attack_cache` are the public functions. There is one attack
implementation for legality, SEE, evaluation and every visual; do not fork it.

## Make and unmake

```python
from chess_observatory.core.make import Board

board = Board(position)  # or Board.from_position(position)
board.make(move)
board.unmake()
snapshot = board.to_position()  # immutable Position
```

`Board` updates bitboards, mailbox, castling, en passant, clocks and the
Zobrist key incrementally. `validate=True` re-checks mailbox/bitboard agreement
and the incremental key after every make; use it in tests, not in perft. The
undo stack belongs to `Board`, never to `Position`.

## Counterfactual edits

Every edit returns `(Position, LegalityReport)` and never silently relaxes a
rule:

```python
from chess_observatory.core.edits import add_piece, remove_piece, swap_kings

edited, report = remove_piece(position, square)
if not report.legal:
    print(report.describe())  # every rule that was relaxed
```

Primitives: `set_piece`, `add_piece`, `remove_piece`, `relocate_piece`,
`set_side`, `clear_castling`, `set_castling`, `set_ep`, `null_move`,
`swap_kings`, plus `inspect_position` for a report without an edit.

```text
LegalityReport(legal: bool, relaxed: frozenset[Relaxation], notes: tuple[str, ...])
```

`Relaxation` names each violated rule (`MISSING_KING`, `ADJACENT_KINGS`,
`CASTLING_WITHOUT_ROOK`, `SIDE_NOT_TO_MOVE_IN_CHECK`, …). UI and reports show
the report whenever a position is not strictly legal, and analyses that depend
on a relaxed rule are labelled accordingly.

## SAN and PGN

```python
from chess_observatory.core.san import parse_san, to_san
from chess_observatory.core.pgn import parse_pgn, iter_pgn, emit_pgn

san = to_san(board, move)  # canonical, with + / # and disambiguation
move = parse_san(board, "Nbd2")  # tolerant parser, raises InvalidSanError

game = parse_pgn(text)  # first game
for game in iter_pgn(stream):  # streaming, text or bytes
    ...
text = emit_pgn(game)  # canonical output
```

`PgnGame` is immutable: headers, a mainline of `PgnNode`, and a game comment.
`PgnNode` carries the move, SAN, comment, NAGs, clock, eval (`eval_cp` /
`eval_mate`) and nested RAVs. `PgnGame` exposes `result`, `start_fen`,
`start_position`, `final_position`, `mainline_moves`, `mainline_uci` and
`to_pgn`. The parser handles `[%clk]`, `[%eval]`, symbolic annotations,
semicolon comments, nested variations and UTF-8/latin-1 input.

## Errors

All errors derive from `ChessObservatoryError` and carry a stable code and a
`context` mapping: `InvalidFenError`, `InvalidSanError`, `InvalidPgnError`,
`IllegalMoveError`.

## Acceptance gate (Phase 1)

- Perft matches the published suite at every tested depth (start, kiwipete and
  positions 3–6), exact.
- 2,000 random games in CI and 100,000 locally produce zero differential
  mismatches: legal move set, terminal status, en-passant flag, FEN after every
  move, and sampled SAN.
- Incremental Zobrist equals a full recompute on every move of every game.
- Branch coverage in `core` is above 95 %.
- `python tools/bench_core.py --check` stays within 50 % of the recorded
  baseline for perft, make/unmake, attack map, SEE, SAN and FEN.

Run the local gate with:

```bash
uv run pytest tests/unit tests/differential -q
uv run python tools/differential.py --games 100000 --san-sample 0
uv run python tools/bench_core.py --check
```
