# ADR-0012: Per-parameter determinism labels

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Every search and analysis parameter declares ALWAYS, TIME_DEPENDENT or HARDWARE_DEPENDENT. The UI shows a Reproducible badge when the active set is deterministic, and reproducibility records are explicit about what cannot be replayed.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `determinism-modes`.*
