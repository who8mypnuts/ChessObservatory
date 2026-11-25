# Search

> **Status:** generated from the parameter registry; regenerate rather than edit.

The promise is "how long to examine, and how" — so search is a
first-class, inspectable subsystem, not a settings dialog
([ADR-0002](adr/0002-hybrid-engine-federation.md)).

## Parameters

| Name | Type | Default | Min | Max | Step | Tier | Determinism | Restart required | Documentation |
|------|------|--------|-----|-----|------|------|-------------|----------------|----------------|
| `search.delta_prune` | bool | true | - | - | 1 | basic | always | False | Enable quiescence delta pruning (Basic tier, deterministic). |
| `search.hash_mb` | int | 256 | 16 | 1024 | 16 | basic | always | True | Transposition-table size in megabytes. |
| `search.max_depth` | int | 32 | 1 | 100 | 1 | intermediate | always | False | Maximum search depth before stopping; 0 means unlimited depth. |
| `search.multipv` | int | 1 | 1 | 32 | 1 | intermediate | always | False | Number of principal variations reported. |
| `search.threads` | int | 1 | 1 | 16 | 1 | basic | hardware_dependent | True | Worker threads; 1 keeps the default node-deterministic search. |

## Reproducibility

- `always` — depth and node limit.
- `time_dependent` — movetime.
- `hardware_dependent` — threads, SIMD paths, GPU inference.

The UI shows a **Reproducible** badge only when the active combination is
deterministic, and reproducibility records state which parameters prevent
replay of a search.

## Related

- [Position API](position-api.md) — the rules core this engine searches.
- [ADR-0002](adr/0002-hybrid-engine-federation.md) — the hybrid engine contract.
