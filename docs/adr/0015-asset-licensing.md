# ADR-0015: Asset and weight licensing ledger

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Every bundled asset and every model weight has an entry in `assets/LICENSES.md` with licence, source and attribution. CI fails on an unlisted asset or a listed file that no longer exists. Engines are never bundled.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `asset-licensing`.*
