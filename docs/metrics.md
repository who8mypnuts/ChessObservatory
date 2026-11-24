# Metrics

> **Status:** generated from the feature registry in Phase 4. This page explains
> the contract now so every later metric is designed against it.

Every metric is declared once ([ADR-0004](adr/0004-feature-registry.md)). The
registry entry carries, at minimum:

| Field | Meaning |
|-------|---------|
| `id` | Stable, namespaced, e.g. `king.safety.shield`. |
| `version` | Bumped when semantics change. |
| `unit` | `pawns`, `squares`, `count`, `ratio`, `centipawns`, `bits`. |
| `category` | Material, structure, king safety, mobility, tension, … |
| `range` | Theoretical min/max, used by scales and heat maps. |
| `symmetry` | How the value transforms under colour mirror / board rotation. |
| `dna_dimension` | Position in the DNA vector, or `None`. |
| `explain` | One sentence for the UI and reports. |
| `trust` | `EXACT`, `DERIVED` or `LEARNED` ([ADR-0005](adr/0005-ai-trust-ladder.md)). |

## Why this is strict

A number without a unit, a range and a symmetry rule cannot be plotted honestly
or tested. The registry turns "add a feature" into a reviewable act, and
`docs/metrics.md` is regenerated from it so the documentation cannot drift.

## What each new metric must ship with

- A hand-computed fixture.
- A mirror/rotation invariance test (or a documented reason it is asymmetric).
- Edge cases: bare kings, no pawns, eight pawns, promotion-heavy positions.
- An explanation sentence used verbatim by the UI.
- A report or panel where it is visible.
- A benchmark if it runs per node or per ply.

## Learned metrics

A learned metric is additive: it appears as its own `LEARNED` row and never
replaces a derived value. Its model id, version and gate report are part of the
record ([ADR-0017](adr/0017-model-governance.md)).
