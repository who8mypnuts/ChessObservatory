# ADR-0019: Assistant grounding and privacy

## Status

Proposed, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

The assistant may only cite facts present in the current analysis bundle. Invented numbers are rejected before display, answers are labelled NARRATIVE, the feature is disabled by default, and remote providers require explicit per-request confirmation. Content lands in Phase 24.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `assistant-grounding`.*
