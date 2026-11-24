# ADR-0010: SQLite for records, Parquet for vectors

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

SQLite (WAL, forward-only migrations) stores positions, games, analyses, notebooks, datasets and model references. Parquet stores corpus-scale float32 columns and dataset shards. Similarity scans never walk SQLite rows.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `store-split`.*
