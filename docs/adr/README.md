# Architecture decision records

One file per decision that shapes the codebase. Format: status, context,
decision, consequences. An ADR is immutable once accepted: change it by
superseding it with a new one.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-own-bitboard-rules-core.md) | Own bitboard rules core | Accepted |
| [0002](0002-hybrid-engine-federation.md) | Hybrid engine: own analytical core plus UCI federation | Accepted |
| [0003](0003-kernel-boundary.md) | Kernel boundary: pure Python reference, numpy batches, optional numba | Accepted |
| [0004](0004-feature-registry.md) | One feature registry for evaluation, DNA, visuals and docs | Accepted |
| [0005](0005-ai-trust-ladder.md) | AI/ML trust ladder (supersedes the original no-ML rule) | Accepted |
| [0006](0006-linux-only.md) | Linux-only target | Accepted |
| [0007](0007-effort-profiles.md) | Effort profiles as first-class presets | Accepted |
| [0008](0008-qtwidgets-design-system.md) | QtWidgets shell plus a custom design system | Accepted |
| [0009](0009-report-ir.md) | One report IR feeding Markdown, HTML and PDF | Accepted |
| [0010](0010-store-split.md) | SQLite for records, Parquet for vectors | Accepted |
| [0011](0011-plugin-api.md) | Versioned public plugin API | Accepted |
| [0012](0012-determinism-modes.md) | Per-parameter determinism labels | Accepted |
| [0013](0013-book-formats.md) | Statistical book plus Polyglot | Accepted |
| [0014](0014-threading.md) | Threading and process model | Accepted |
| [0015](0015-asset-licensing.md) | Asset and weight licensing ledger | Accepted |
| [0016](0016-visual-qa.md) | Bounded visual regression matrix | Accepted |
| [0017](0017-model-governance.md) | Model governance and parity gates | Accepted |
| [0018](0018-theme-pack-system.md) | Theme packs as data (20 shipped themes) | Accepted |
| [0019](0019-assistant-grounding.md) | Assistant grounding and privacy | Proposed |
| [0020](0020-training-reproducibility.md) | Training reproducibility | Proposed |

## When an ADR is required

- A locked decision (plan §2) changes.
- A new cross-cutting dependency or runtime boundary is introduced.
- A subsystem gains a public contract (API, file format, plugin surface).
- A test, gate or security guarantee is weakened.

Small implementation choices do not need an ADR; they need a test.
