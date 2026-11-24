# Chess Observatory documentation

The implementation plan is the source of truth for *what* is built and in which
order. This directory is the source of truth for *how it works and how to use
it*.

## Start here

- [Architecture](architecture.md) — layering, dependency rules, threading.
- [Position API](position-api.md) — the rules-core surface (Phase 1).
- [Search](search.md) — every engine parameter and what it does (Phase 2).
- [Metrics](metrics.md) — the feature registry reference (Phase 4).
- [Models](models.md) — model cards, gates, trust labels (Phase 15).
- [Themes](themes.md) — the 20 theme packs and board palettes (Phase 6).
- [User guide](user/README.md) — what each panel does, task by task.
- [Gallery](gallery/README.md) — approved reference screenshots.
- [Architecture decisions](adr/README.md) — ADR-0001 … ADR-0020.

## Conventions

- Every command in these pages is copy-pasteable from the repository root.
- Every number has a unit and a source.
- Screenshots are reference images, not decoration: they are checked in CI.
- If a page and the code disagree, the code is wrong or the page is wrong —
  either way, one of them changes in the same commit.
