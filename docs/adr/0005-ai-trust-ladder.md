# ADR-0005: AI/ML trust ladder (supersedes the original no-ML rule)

## Status

Accepted, 2026-11-23.

## Context

The original brainstorm forbade AI/ML outright to protect one property: a reader
must be able to tell a measured fact from a guess. The owner has since allowed
learned components. Removing the rule without replacing the protection would be
the actual mistake.

## Decision

Every output carries exactly one label:

| Label | Backed by | Example |
|-------|-----------|---------|
| `EXACT` | exhaustive enumeration or an independent verifier | tablebase, proof tree, perft |
| `DERIVED` | a named deterministic algorithm | features, DNA, motif detectors, graph centrality |
| `LEARNED` | a versioned model plus a gate report | neural eval, policy, embeddings |
| `NARRATIVE` | generated prose grounded in the above | assistant explanations |

Rules:

- The label is declared, never defaulted; a test enumerates producers.
- An `AnalysisResult` is labelled with the weakest label among its contents unless
  the contents are explicitly partitioned.
- A model may **propose**, never **certify**: fortress candidates are proved,
  puzzles are verified by search, tablebase claims are exact.
- The classical path is always present. `ml.enabled=false` is a tested product
  mode, not a degraded one.
- The UI has `Verified only` and `Hide learned` filters, and reports print a trust
  legend with model cards.

## Consequences

- Learned features are additive and optional; the instrument remains honest with
  every model deleted.
- Explanations must say which part is measured and which part is learned, even
  when both contribute to one number.
- Model changes are release-visible (ADR-0017).

## Alternatives considered

- *No ML at all*: safe but leaves real capability on the table; superseded by the
  owner's decision on 2026-11-23.
- *ML with a global disclaimer*: cheap, and exactly the failure mode this ADR
  exists to prevent.

*Slug: `ai-trust-ladder`.*
