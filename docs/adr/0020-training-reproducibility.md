# ADR-0020: Training reproducibility

## Status

Proposed, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Datasets have sha256 manifests and stored deterministic splits; training configs pin seeds, versions and hardware assumptions; two identical smoke runs must produce the same manifest and artifact hash. Full training is never CI work; a tiny smoke run is. Content lands in Phase 15.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `training-reproducibility`.*
