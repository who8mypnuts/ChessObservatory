# Search

> **Status:** the parameter registry and search arrive in Phase 2. Until then the
> only search-related settings are defaults in the configuration file.

The promise is "how long to examine, and how" — so search is a first-class,
inspectable subsystem, not a settings dialog ([ADR-0002](adr/0002-hybrid-engine-federation.md)).

## Configuration available now

| Key | Default | Meaning |
|-----|---------|---------|
| `search.default_profile` | `standard` | Effort profile used when none is chosen. |
| `search.threads` | `1` | Threads; 1 is the reproducible default. |
| `search.hash_mb` | `256` | Transposition-table size. |

Set them in `~/.config/chess-observatory/config.toml`, with
`CHESS_OBS_SEARCH_THREADS`, or per command with `--set search.threads=4`.

## What Phase 2 adds

One parameter registry declares every knob once (name, type, range, default,
tier, determinism, restart requirement, documentation). From it we generate:

- CLI flags;
- UCI `setoption` names and types;
- settings controls, grouped Basic / Intermediate / Expert / Experimental;
- this page (`docs/search.md` becomes generated, not hand-written);
- configuration round-trip and migration tests.

## Determinism

Every parameter is labelled:

- `ALWAYS` — depth, node limit;
- `TIME_DEPENDENT` — movetime;
- `HARDWARE_DEPENDENT` — threads, SIMD paths, GPU inference.

The UI shows a **Reproducible** badge only when the active combination is
deterministic, and reproducibility records state which parameters prevent replay
([ADR-0012](adr/0012-determinism-modes.md)).

## Effort profiles

`Quick`, `Standard`, `Deep`, `Exhaustive` and `Proof` are named expansions of
analyzer budgets and search limits. `Proof` never uses GPU inference.
