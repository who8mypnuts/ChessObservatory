# Architecture

Chess Observatory is a research instrument: it explains *why* a position works,
and it must never confuse a measured fact with a guess. The architecture serves
both goals by keeping computation, presentation and provenance separate.

This page describes the target structure and the rules that hold from Phase 0
onward. Components that do not exist yet are marked with the phase that adds
them.

## Layers

Dependencies point downward only.

```
ui/          PySide6 workspace, design system, board, panels          (Phase 6)
cli/         thin commands: doctor, config, ui, later analyze/labs
services/    use-cases that combine analysis, store and exports       (Phase 5)
analysis/    analyzers, job system, cache, effort profiles            (Phase 5)
reports/     document IR and Markdown/HTML/PDF exporters               (Phase 19)
plugins/     versioned public API and loader                           (Phase 25)
ml/          encodings, registry, inference, datasets, training        (Phase 15)
learned/     model-backed evaluators and perception labs               (Phase 17+)
eval/        feature registry, terms, decomposition, explanations      (Phase 4)
search/      own engine: parameters, TT, ordering, trace               (Phase 2)
uci/         external engine federation, consensus, tournaments        (Phase 3)
store/       SQLite records, Parquet vectors, migrations               (Phase 14)
core/        bitboards, position, movegen, attacks, make/unmake        (Phase 1)
kernels/     pure/numpy/numba backends behind one API                  (Phase 2)
config.py    typed layered configuration                    (implemented)
health.py    environment diagnosis                          (implemented)
errors.py    error taxonomy                                 (implemented)
logging.py   rotating file + console logging                (implemented)
serialization.py  canonical JSON and strict decoding        (implemented)
paths.py     XDG locations                                  (implemented)
```

The current tree implements the bottom band only. That is deliberate: the
foundation is testable before any chess code exists.

## Dependency rules (enforced by a test)

| Rule | Why |
|------|-----|
| `PySide6` only in `ui/` | The CLI and analyzers must run headless. |
| `python-chess`, `networkx` never in `src/` | They are test oracles, not runtime dependencies (ADR-0001). |
| `numba` only in `kernels/` | One optional accelerator boundary (ADR-0003). |
| `torch` only in `ml/training/` | Training is not runtime. Inference uses ONNX Runtime. |
| `onnxruntime` only in `ml/inference/` | One inference boundary (ADR-0017). |
| `chess_observatory.ui` imported only by `ui/` and `cli/` | No analyzer may reach into widgets. |
| No `sys.path` manipulation | Installed packages only. |

The guard parses the source tree; it is not a convention. See
`tests/unit/test_import_graph.py`.

## Contracts

The plan defines a small number of cross-cutting contracts (position API, layer,
chart, analysis result, report document, parameter registry, feature registry,
theme tokens, trust labels, model registry). The rule is that a feature attaches
to an existing contract rather than inventing a parallel one. Implemented so far:

- **Errors**: one taxonomy with stable codes and actionable hints
  (`src/chess_observatory/errors.py`).
- **Configuration**: defaults → user TOML → environment → CLI, with per-value
  provenance and forward-only migration (`config.py`; plan §13.5).
- **Serialization**: canonical JSON with sorted keys and strict typed decoding
  (`serialization.py`).
- **Health**: independent, guarded checks that produce a structured report
  (`health.py`).
- **Trust labels**: `EXACT`, `DERIVED`, `LEARNED`, `NARRATIVE` ([ADR-0005](adr/0005-ai-trust-ladder.md)).

## Process and threading model (target)

- The GUI thread never blocks for more than 50 ms. Analysis runs in a job system
  with cancellation and progress events.
- External engines are subprocesses with watchdogs, timeouts and kill escalation.
- numpy and ONNX Runtime release the GIL for batch work; numba kernels are called
  with explicit array layouts.
- Every search and analysis records enough to replay it: seeds, parameter hashes,
  engine ids/versions, model hashes ([ADR-0012](adr/0012-determinism-modes.md)).

## Data (target)

- SQLite in WAL mode for positions, games, analyses, notebooks, datasets and
  model references, with forward-only tested migrations.
- Parquet for corpus-scale float32 vectors and dataset shards.
- Model artifacts live outside the repository, addressed by sha256
  ([ADR-0017](adr/0017-model-governance.md)).

## What Phase 0 actually builds

| Area | Module | Proof |
|------|--------|-------|
| Errors | `errors.py` | unique codes, hints, hierarchy test |
| Paths | `paths.py` | XDG environment tests |
| Config | `config.py` | precedence, migration, validation, round-trip |
| Serialization | `serialization.py` | canonical output, strict decode |
| Logging | `logging.py` | file+console, no duplicate handlers |
| Health | `health.py` | structured report, guarded checks |
| CLI | `cli/` | doctor, config, ui, version, exit codes |
| UI shell | `ui/` | offscreen window test |
| Guards | `tests/` | import graph, asset ledger, docs freshness |

The next layer to land is the rules core in Phase 1; see
[Position API](position-api.md).
