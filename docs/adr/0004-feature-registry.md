# ADR-0004: One feature registry for evaluation, DNA, visuals and docs

## Status

Accepted, 2026-11-23.

## Context

The same positional fact appears in several places: an evaluation term, a DNA
dimension, a heat map, a report sentence, a graph annotation. Implemented
separately, those copies drift, and the documentation drifts fastest of all.

## Decision

Every metric is declared once, with metadata:

```
MetricSpec(id="king.safety.shield", version=1, unit="pawns", category=...,
           dna_dimension=..., explain=..., symmetry=..., range=...)
```

Consequences are automatic: `docs/metrics.md` is generated from the registry, the
DNA vector is built from registered dimensions, the explanation panel reads
`explain`, and tests require a fixture and a symmetry check per metric.

A metric without an entry does not ship.

## Consequences

- Adding a metric is a small, reviewable, documented act.
- Renaming or changing semantics requires a version bump, so stored DNA vectors
  and cached analyses stay interpretable.
- The registry is the single place to audit for "numbers theatre" (risk R3).

## Alternatives considered

- *Per-subsystem metric definitions*: faster to write, guaranteed to drift.
- *Documentation generated from docstrings*: prose without units or guarantees;
  the registry carries structured facts instead.

*Slug: `feature-registry`.*
