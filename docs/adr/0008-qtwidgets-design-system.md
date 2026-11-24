# ADR-0008: QtWidgets shell plus a custom design system

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

The application is QtWidgets with custom-painted components driven by design tokens. QML islands are allowed only if a specific visual proves impossible otherwise. Every interactive control is styled; stock Qt appearance is a defect.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `qtwidgets-design-system`.*
