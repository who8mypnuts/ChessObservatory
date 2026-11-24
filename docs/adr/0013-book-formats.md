# ADR-0013: Statistical book plus Polyglot

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

The book layer reads and writes our statistical format and reads Polyglot `.bin` against the published spec with byte-level tests. Book play is off by default in analysis so results stay explainable; a learned book is not planned for v1.0.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `book-formats`.*
