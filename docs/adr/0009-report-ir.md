# ADR-0009: One report IR feeding Markdown, HTML and PDF

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Reports are built as a typed document IR, then rendered by interchangeable exporters, so screen, HTML and `QPdfWriter` output cannot drift. Figures come from the same `Layer`/`ChartSpec` contracts as the workspace.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `report-ir`.*
