# Position API

> **Status:** defined by Phase 1. This page is the contract the rest of the
> project codes against; it is written before the implementation so the shape is
> reviewed first.

The rules core lives in `chess_observatory.core` and has no runtime third-party
dependencies ([ADR-0001](adr/0001-own-bitboard-rules-core.md)).

## Representation

- **Square**: `0 = a1` … `63 = h8`, a `NewType` over `int`.
- **Move**: packed 32-bit integer (`from`, `to`, promotion, flags), a `NewType`.
- **MoveList**: `array('i')` of packed moves, not a list of objects.
- **Position**: immutable snapshot — 12 piece bitboards plus occupancy, a
  `bytes(64)` mailbox, side to move, castling rights, en-passant square, clocks,
  and a `strict` flag.
- **ZobristKey**: splitmix64 with a fixed seed; incremental updates must equal a
  full recompute in property tests.

## Operations

| Operation | Notes |
|-----------|-------|
| `piece_at(square)` | mailbox lookup |
| `legal_moves()` | pseudo-legal generation plus pin/check filtering |
| `make_move(move)` / `undo()` | undo stack owned by the mutable engine state, not `Position` |
| `attackers_to(square, occupancy)` | one implementation for the whole project |
| `attack_map()` | per-square attackers/defenders, pins, checks, x-ray, safe-to-occupy |
| `apply_edit(edit)` | returns a `LegalityReport`; never silently relaxes rules |

## Experimental states

The instrument needs positions a conventional library refuses: edited castling
rights, impossible material, "wrong" side to move. These are first-class, but
every construction path says what was relaxed:

```text
LegalityReport(legal: bool, relaxed: frozenset[Relaxation], notes: tuple[str, ...])
```

UI and reports show the report whenever a position is not strictly legal, and
analyses that depend on a relaxed rule are labelled accordingly.

## Oracles

`python-chess` is the differential oracle for legality, perft, FEN, SAN and PGN.
It is a development dependency only; CI fails if `src/` imports it.

## Acceptance gate (Phase 1)

- Perft matches the published suite at every tested depth.
- 100k random games produce zero differential mismatches locally, 2k in CI.
- Incremental Zobrist equals recompute on every move of every game.
- Mirror and rotation invariance hold for the attack map.
