# ADR-0011: Versioned public plugin API

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Entry points are versioned from day one: analyzers, engines, report sections, charts, importers and inference backends. Manifests declare permissions; a conformance suite runs before a plugin loads; the API stabilises at v1.0.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `plugin-api`.*
