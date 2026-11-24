# ADR-0001: Own bitboard rules core

## Status

Accepted, 2026-11-23.

## Context

Legality looks like a solved problem, so importing an existing library is the
obvious shortcut. It is the wrong one here. The product depends on inspecting
positions that a conventional library refuses to construct: edited castling
rights, a side that "should" not be to move, impossible-but-interesting material,
counterfactual branches that never occurred. The engine also needs bitboards,
incremental Zobrist keys and make/unmake on the hot path, none of which a
general-purpose library exposes with the right performance profile.

## Decision

Implement the rules core in `chess_observatory.core`:

- 64-bit bitboards, packed 32-bit moves, immutable `Position` snapshots.
- One implementation of "what attacks this square" (`core/attacks.py`), used by
  legality, SEE, tactics, influence, king safety and the graph views.
- Position edits return a `LegalityReport` describing exactly which rules were
  relaxed. Nothing is silently accepted.
- `python-chess` and `networkx` are **test-only oracles**, never runtime
  dependencies. An import-graph test enforces this.

## Consequences

- Perft, differential and property tests must be excellent; correctness is now
  our responsibility. This is budgeted in Phase 1 and is the gate for the phase.
- The experimental API is a feature, not a loophole: every relaxed rule is named
  and surfaced in the UI.
- No third-party licence or API change can break the core.
- Performance work is explicit (kernels boundary, ADR-0003) rather than assumed.

## Alternatives considered

- *`python-chess` at runtime*: fast to start, but cannot represent the states the
  research features need, and hides the attack map we want to expose.
- *Ask Stockfish for legality over UCI*: absurd latency for a core primitive and
  makes offline operation fragile.

*Slug: `own-bitboard-rules-core`.*
