---
date: 2026-11-23
status: plan
tags:
- chess
- implementation-plan
- architecture
- pyside6
- pyside6-qt
- machine-learning
- testing
title: Chess Observatory --- Implementation Plan
related:
- chess_observatory_project_brainstorm.md
- chess_observatory_project_pitch.md
---

# Chess Observatory — Implementation Plan

> A chess engine tells you what move to play. Chess Observatory should help
> you understand the entire computational universe surrounding that move.

This document converts the brainstorm into an ordered, testable build plan.
Scope is **complete**: every feature in the brainstorm is assigned to a phase
(§3). Nothing is deferred to a "someday" list.

---

## 1. How To Use This Plan

- Work **phase by phase**. Do not start a phase until the previous gate passes.
- Work **step by step** inside a phase. One step = one reviewable change.
- Every step inherits the **Standard of Done** (§13.1). Nothing is "done"
  because it runs.
- If a step proves a locked decision (§2) wrong, stop and write an ADR (§13.6)
  before writing code.
- Anything marked **[ASK]** is a real open question with a working default.
- Phase effort figures are *focused development days* for one experienced
  developer. They are planning envelopes, not promises.
- On a new machine, start with `./setup.sh` (Phase 0). It diagnoses, installs,
  verifies, and prints the launch command; `./setup.sh --check` diagnoses
  without changing anything.

---

## 2. Locked Decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Engine strategy | **Own engine as the analytical core**, plus a first-class federation of external UCI engines as reference oracles |
| D2 | Rules core | **Own** bitboard core; `python-chess` is a **test-only** differential oracle |
| D3 | Performance path | Pure Python first behind a narrow kernel boundary; numpy for batch math; numba as an optional extra |
| D4 | v0.1 scope | Instrument MVP: core + search federation + decomposed eval + DNA + geometry/influence + graphs + designed workspace + report export |
| D5 | Toolchain | Python 3.14, `uv`, PySide6 6.12, numpy 2.x, onnxruntime 1.32, torch 2.15, faiss-cpu 1.16 — all verified resolvable for 3.14 on 2026-11-23 |
| D6 | Audience | Both: one professional workspace plus layout presets (`Simple`, `Research`, `Tactics`) |
| D7 | AI/ML policy | **ML, neural networks and LLMs are allowed**, but every output carries an epistemic label: `EXACT` (tablebase/proof), `DERIVED` (algorithm), `LEARNED` (model), `NARRATIVE` (generated text). The classical path is always available and never silently replaced |
| D8 | License | MIT for our code; dependencies must be MIT/BSD/Apache/ISC-compatible |
| D9 | Platforms | **Linux only** (X11 + Wayland). AppImage as primary artifact, Flatpak optional |
| D10 | External engines | Pluggable registry with ≥ 4 open-source engines preconfigured (Stockfish, Berserk, Ethereal, RubiChess, plus Igel); **never bundled**, detected or user-installed, license-aware |
| D11 | Reports | Markdown + HTML + **PDF via `QPdfWriter`** from the first reporting phase, not later |
| D12 | Opening knowledge | ECO name table **and** an opening book system: own book format, Polyglot `.bin` reader, book builder, book statistics |
| D13 | Plugins | **Public, versioned plugin API in v1.0** for analyzers, engines, report sections, chart types, and data importers |
| D14 | Scope | **No deferral.** Every brainstorm item (§3) ships by v1.0 |
| D15 | UI approach | QtWidgets shell + custom-painted components + a formal design system (ADR-0008). QML not used for the shell; QML "islands" allowed only if a specific view demands it |
| D16 | Network | Local-first runtime. Network is touched only by explicit, user-initiated actions: engine install, model download, or an assistant request |
| D17 | ML runtime | **ONNX Runtime** for inference (CPU default, optional CUDA/ROCm provider); **PyTorch** used for training only. Every model is an optional, checksummed download |
| D18 | Model governance | Model registry + model cards; models are versioned artifacts; no silent upgrade ever; a learned component may only replace a derived one after passing parity gates (§6.16) |
| D19 | Themes | **20 theme packs** (12 dark, 6 light, 2 accessibility/greyscale) plus independent board palettes; token-driven, zero hardcoded colours, every theme WCAG-checked |
| D20 | Assistant | LLM narration/Q&A is **opt-in, local-first**, strictly grounded in computed analysis results, labelled `NARRATIVE`, and never allowed to write numbers into an analysis |
| D21 | Training | Training is offline-only, reproducible (seeds + dataset hashes + pinned versions), and never runs in CI; CI tests inference and data pipelines only |

### 2.1 AI/ML policy: the trust ladder (D7)

> **Supersedes the brainstorm.** The original brainstorm forbade AI/ML outright.
> By the owner's decision on 2026-11-23 that constraint is replaced by the policy
> below. The brainstorm's other constraints (explicit algorithms, no black-box
> truth claims) still hold.

The project's credibility comes from separating *what is proven* from *what is
computed* from *what is guessed*. Every value, finding and sentence carries one
of four labels:

| Label | Meaning | Examples | Guarantees |
|-------|---------|----------|------------|
| `EXACT` | Mathematically exhaustive within a stated domain | tablebase WDL/DTM, verified proof tree, perft counts, retrograde results | independently verifiable; a verifier or exhaustive enumeration backs it |
| `DERIVED` | Deterministic result of a named algorithm with stated inputs | feature values, DNA dimensions, motif detections, graph centrality, classical eval terms | reproducible bit-for-bit on the same inputs |
| `LEARNED` | Output of a versioned model | NN evaluation, policy priors, embeddings, motif classifier, difficulty estimate | reproducible only within the model's determinism envelope; model card + hash recorded |
| `NARRATIVE` | Generated prose | assistant explanations, drafted report paragraphs | grounded citations to `EXACT`/`DERIVED`/`LEARNED` facts; text is never a source of numbers |

Consequences, enforced in code and UI:

1. `Trust` is a required field on `Finding`, `Metric`, `Explanation` and report
   figures. There is no unlabelled output path.
2. The UI shows a small trust badge on every claim, and offers filters
   (`Verified only`, `Hide learned`, `Hide narrative`).
3. Reports print a trust legend and cite the model card for every `LEARNED`
   figure.
4. A model may **propose** but never **certify**: proofs and tablebases stay
   symbolic. A network can suggest "this looks like a fortress"; only bounded
   proof search may claim it.
5. Everything works with `ml.enabled = false`. That configuration is a
   first-class, tested product mode — not a fallback.


### 2.2 Consequence of Linux-only (D9)

- CI: Ubuntu runners only; UI tests headless via `QT_QPA_PLATFORM=offscreen`.
- Packaging: AppImage (primary), Flatpak optional; no Windows/macOS builds.
- Two real display stacks must be smoke-tested manually each release: X11 and
  Wayland (fractional scaling, no global cursor positioning, no frameless
  tricks that break tiling WMs).

---

## 3. Scope Traceability

Every brainstorm item, mapped. This table is the contract that "nothing was
dropped".

### 3.1 Analytical subsystems (brainstorm §2, §3)

| Item | Feature | Phase |
|------|---------|-------|
| A | Position DNA fingerprint + comparable positions | 7 |
| B | Tactical Universe (motifs, dependency chains, latent tactics) | 10 |
| C | Attack and Defense Graph + graph algorithms | 9 |
| D | Counterfactual Chess laboratory | 12 |
| E | Strategic Horizon Analysis | 13 |
| F | Chess Complexity Analyzer | 13 |
| G | Move Uniqueness and Criticality | 13 |
| H | Evaluation Decomposition Engine | 4 |
| I | Endgame Tablebase Laboratory (retrograde, DTM/DTZ, own format) | 18 |
| J | Chess Geometry Laboratory (influence density, heat maps) | 8 |
| K | Pawn Structure Research Engine + transition graph | 11 |
| L | The Chess Microscope (6 modes) | 8 |
| M | Exchange Consequence Analyzer + exchange tree | 12 |
| N | Fortress and Defensive Resource Detector | 18 |
| O | Opening Structure Genealogy | 19 |
| P | Position Autopsy | 19 |
| Q | Proof-Carrying Chess Analysis (AND/OR tree + verifier) | 18 |
| R | Search Space Observatory (live + replayable tree) | 20 |
| S | Position Similarity Engine (indexed corpora) | 16 |
| T | Analysis of Analysis (confidence profile) | 13 |

### 3.2 Interface and workspace (brainstorm §6)

| Idea | Phase |
|------|-------|
| Dockable, resizable, independently configurable panels | 6 |
| Full-screen tactical exploration mode | 10 (basic), 20 (full workspace modes) |
| Graph visualization mode | 9, polished 20 |
| Position comparison mode | 12 |
| Game timeline with important events | 19 |
| Heat-map overlay system | 8 |
| Multi-board comparison workspace | 20 |
| Search-tree explorer | 20 |
| Analysis notebook recording findings and variations | 20 |
| Professional workstation look and feel (design system) | 6, enforced every phase |
| Useful without ever touching conventional engine evaluation | Design rule (§6.9) |

### 3.3 Wild ideas (brainstorm §8)

| # | Idea | Phase |
|---|------|-------|
| 1 | Chess Entropy | 22 |
| 2 | Sacrifice Laboratory | 22 |
| 3 | Forced Move Detector | 22 |
| 4 | King Safety Simulator | 22 |
| 5 | The Exchange Economy | 23 |
| 6 | Chess Archaeology | 23 |
| 7 | Positional Fragility | 23 |
| 8 | Move Consequence Explorer | 23 |
| 9 | Theoretical Novelty Detector | 23 |
| 10 | Chess Mathematics Explorer (zugzwang, opposition, triangulation, domination) | 23 |

### 3.4 Project notes (brainstorm §11)

| Note | Resolution |
|------|-----------|
| Independent vs hybrid vs platform | Hybrid federation (§2 D1, §8) |
| Primary audience | Both, one workspace + presets |
| AI/ML governance | §2.1 trust ladder, §6.15–§6.16, ADR-0005 + ADR-0017 |
| Language and platform | Python 3.14 + PySide6, Linux (§2 D5, D9) |
| Position-core API | Defined in Phase 1, documented in `docs/position-api.md` |
| First three analytical subsystems | **DNA (7), Geometry/Influence (8), Tactics (10)** — chosen because they share the attack map and validate the DRY contracts early |
| Initial technical architecture | §4–§14, ADR-0008…ADR-0020 |
| Existing engines to study | §8.2 registry (Stockfish, Berserk, Ethereal, RubiChess, Igel, Lc0, Maia) |
| Measurable goals | §12 budgets, §14 gates, §16 release map |

### 3.5 AI/ML Capability Map

With D7 unlocked, everything the no-ML rule formerly forbade comes back on the
table. This is the deliberate inventory: what AI can add, where it plugs in, and
what I recommend.

† = previously excluded by the old no-ML constraint.

**Decisions taken 2026-11-23:** approved — 11 difficulty/human-likeness,
12 board-image recognition, 13 style profiling, 14 puzzle generation,
15 repertoire recommendation, 18 blunder-risk prediction. Dropped —
16 learned book, 17 coach mode, 19 engine-assistance detection, 20 personal
model. Neural evaluation (Q10) stays opt-in through v1.0.

| Capability | Phase | What it adds | Stance |
|-----------|-------|--------------|--------|
| Learned evaluation (NNUE-style / small CNN) † | 17 | positional judgement beyond hand-set terms | **Adopt** as an *additional* evaluator, parity-gated |
| Policy prior + MCTS search mode † | 17 | narrower search, AlphaZero-style exploration | **Adopt** as an optional mode |
| Gradient-based weight tuning for classical terms † | 17 | escapes the hand-tuning ceiling | **Adopt** |
| Self-play data generation + training loop † | 15–17 | continual improvement with SPRT gates | **Adopt** (offline) |
| Learned position embeddings † | 16 | "feels like" similarity, latent-space DNA | **Adopt** as an extra metric |
| ANN index (HNSW / faiss) for corpora † | 16 | similarity at 10M+ positions | **Adopt**, optional dependency |
| Learned motif / combination classifier † | 21 | catches tactical patterns hand rules miss | **Adopt**, second opinion only |
| Difficulty estimation and human-likeness (Maia-style) † | 21 | "what would a 1600 play?", puzzle ratings | **Adopt** — opt-in, calibrated, `LEARNED` |
| Board-image recognition (paste a screenshot) † | 21 | position capture from diagrams/photos | **Adopt** — manual confirmation always required |
| Player style profiling and clustering † | 21 | repertoire and style coaching | **Adopt** — per-axis evidence shown |
| Puzzle generation with calibrated difficulty † | 21 | training material from your own games | **Adopt** — uniqueness proved by search |
| Opening repertoire recommendation † | 21, 23 | ranked repertoire by style/level | **Adopt** — explainable via features + statistics |
| Learned opening book (policy priors) | 14, 17 | stronger, style-aware book | **Not planned for v1.0** — statistical book + Polyglot only |
| Assistant: natural-language explanations and Q&A † | 24 | accessibility; "why" in words | **Adopt**, opt-in |
| Assistant: report drafting † | 24 | faster, polished prose with grounded citations | **Adopt**, opt-in |
| Coach mode (interactive lessons) † | 24 | teaching workflows over verified findings | **Not planned for v1.0** — a second product |
| Fortress / defensive-resource candidate generation † | 18 | proposes candidates for proof verification | **Adopt**, proposal only |
| Blunder-risk and human-error prediction † | 21 | richer autopsy ("what a human misses here") | **Adopt** — confidence intervals, explicit error rates |
| Approximate tablebases via networks | — | smaller footprint | **Not planned** — breaks `EXACT` |
| Learned centrality for piece graphs (GNN) | 9 | possibly better importance ranking | **Not planned** — destroys interpretability |
| Engine-assistance / cheating detection | 21 | integrity analysis for events | **Not planned** — false-positive harm outweighs value |
| Personal model trained on your own games | 21 | style-matched analysis | **Not planned** — privacy and data-volume cost |
| Auto-labelling to bootstrap training sets † | 15, 21 | accelerates dataset building | **Adopt**, labels verified before use |

Rules for every adopted row:
1. The classical/derived path stays and is never removed.
2. A learned component ships only with a model card, a hash, and a parity gate.
3. Its outputs are labelled `LEARNED` and are filterable in UI and reports.
4. Anything that claims a definitive chess result must be re-verifiable by
   search, tablebase, or proof.

---

## 4. Architecture

### 4.1 Layering (dependencies point downward only)

```
┌──────────────────────────────────────────────────────────────────┐
│ ui/            PySide6 workspace, design system, board, panels   │
├──────────────────────────────────────────────────────────────────┤
│ cli/           commands: analyze · dna · similar · autopsy ·      │
│                experiment · engines · doctor · book               │
├──────────────────────────────────────────────────────────────────┤
│ services/      The only API front-ends may call. Workflows:       │
│                open, move, analyze, compare, edit, export,        │
│                search, experiment, engine management              │
├──────────────────────────────────────────────────────────────────┤
│ analysis/      Analyzer registry, pipeline DAG, JobRunner,        │
│                cache, effort profiles, AnalysisResult, report IR  │
├──────────────────────────────────────────────────────────────────┤
│ domain: dna · geometry · graphs · tactics · counterfactual ·      │
│         horizon · complexity · criticality · pawn · endgame ·     │
│         proof · similarity · opening · autopsy · genealogy ·      │
│         labs/* · store/ · experiments/ · reports/ · plugins/      │
├──────────────────────────────────────────────────────────────────┤
│ assistant/     LLM adapter, grounding, prompt templates, cache    │
├──────────────────────────────────────────────────────────────────┤
│ ml/            encodings · model registry · inference backends ·  │
│                datasets · training harness · self-play · gates    │
├──────────────────────────────────────────────────────────────────┤
│ eval/          Feature registry, terms, decomposition, explain    │
│ search/        negamax, TT, ordering, limits, traces, parallel    │
│ uci/           client, server, registry, quirks, consensus        │
├──────────────────────────────────────────────────────────────────┤
│ core/          Position, movegen, make/unmake, Zobrist, FEN, SAN, │
│                PGN, attacks, edits (counterfactual primitives)    │
└──────────────────────────────────────────────────────────────────┘
```

**Enforced rules**
- `core` imports nothing from this project (`ml/` may import `core`).
- Only `ui/` may import PySide6 (import-graph test).
- Only `tests/` may import `python-chess` or `networkx` (import-graph test).
- `torch` may only be imported by `ml/training/`; inference uses ONNX Runtime
  behind `ml/inference/` (import-graph test, so a missing CPU install never
  breaks the app).
- `cli` and `ui` never call analyzers directly — only `services/`.
- Analyzers receive immutable `Position` snapshots; only `core`/`search` mutate
  a working `Board`.
- No module-level mutable singletons; a `RuntimeContext` is passed explicitly.

### 4.2 Why `services/`

It is what keeps the GUI thin and guarantees CLI parity: if a capability cannot
be expressed as a service call, it is a design smell. This is the primary
defence against "the GUI became the program".

### 4.3 Threading model

- All long work runs through `JobRunner`: `InlineRunner` (tests),
  `ThreadRunner` (numpy/IO), `ProcessRunner` (pure-Python CPU work).
- Python threads do **not** speed up pure-Python search (GIL). Real parallelism
  comes from (a) multiple concurrent jobs as processes, (b) numba kernels with
  `nogil=True`, (c) root-splitting across processes for deep searches.
- Neural inference runs in a worker thread with a **bounded** batch queue;
  ONNX Runtime releases the GIL, so this genuinely overlaps with searching.
- The GUI thread only paints and dispatches. A debug watchdog asserts no
  handler blocks > 50 ms.

---

## 5. Package Layout

```
ChessObservatory/
├── pyproject.toml · uv.lock · README.md · LICENSE · setup.sh
├── docs/
│   ├── adr/                  ADR-0001 … ADR-0020
│   ├── architecture.md
│   ├── position-api.md
│   ├── metrics.md            generated from the feature registry
│   ├── search.md             every search parameter and what it does
│   ├── models.md            model cards, gates, and benchmark results
│   ├── themes.md             theme packs, palettes, accessibility notes
│   ├── user/                 per-panel user guide
│   └── gallery/              reference screenshots per milestone
├── src/chess_observatory/
│   ├── core/       squares · pieces · moves · position · board · movegen
│   │               attacks · make · zobrist · fen · san · pgn · edits
│   ├── kernels/    __init__ (backend selection) · pure · numpy_k · numba_k
│   ├── search/     params · limits · tt · ordering · engine · qsearch
│   │               parallel · trace · presets · uci_options
│   ├── uci/        protocol · client · server · registry · quirks
│   │               manager · consensus · tournament
│   ├── eval/       registry · features/* · terms · decomposition
│   │               explain · presets
│   ├── analysis/   analyzer · pipeline · jobs · cache · results
│   │               effort · render · report_ir
│   ├── dna/        schema · compare · report · analyzer
│   ├── geometry/   influence · mobility · king · layers · microscope
│   ├── graphs/     build · algorithms · layout · diff · render_data
│   ├── tactics/    motifs · dependencies · latent · verify · suite
│   ├── counterfactual/ spec · apply · diff · scenarios · lab · exchange
│   ├── horizon/    curve · events · timeline
│   ├── complexity/ metrics · classify
│   ├── criticality/ metrics · uniqueness
│   ├── endgame/    tb_format · retrograde · probe · explorer · fortress
│   ├── proof/      tree · build · verify
│   ├── store/      schema · migrations · bulk · import_pgn · integrity
│   │               backup · corpus
│   ├── opening/    eco · book_format · polyglot · builder · stats · novelty
│   ├── similarity/ index · query · buckets
│   ├── autopsy/    events · rules · narrative
│   ├── genealogy/  cluster · families
│   ├── labs/       entropy · sacrifice · forced · kingsim · economy
│   │               archaeology · fragility · consequence · mathx
│   ├── experiments/ spec · runner · stats · sprt · report
│   ├── reports/    document · templates · exporters (md/html/pdf) · figures
│   ├── plugins/    api · loader · manifest · conformance
│   ├── ml/
│   │   ├── encoding/   board planes · history · move indices · augmentations
│   │   ├── models/     registry · manifest · cards · downloads · integrity
│   │   ├── inference/  backend protocol · onnx · torch · batched queue
│   │   ├── datasets/   builders · splits · provenance · hashing · filtering
│   │   ├── training/   loop · configs · checkpoints · metrics · seeds
│   │   ├── selfplay/   generator · labeling · storage
│   │   └── gates/      parity vs classical · calibration · latency · ablation
│   ├── learned/    eval_nn · policy · embeddings · motif_clf · difficulty
│   │               human_like · style · vision (board-image recognition)
│   ├── assistant/  adapter · grounding · prompts · cache · redaction
│   ├── services/
│   ├── cli/
│   └── ui/
│       ├── app.py · main_window.py · bus.py · session.py
│       ├── design/    tokens · theme · qss · icons · motion · theme_packs
│       ├── components/ buttons · chips · sliders · tabs · cards · toasts
│       │               skeletons · toolbars · segmented · tables · trust_badge
│       ├── board/      widget · overlays · pieces · drag · promotion · coords
│       ├── charts/     line · area · stacked · radar · gauge · timeline
│       │               heatlegend · sparkline · graphview
│       ├── panels/     one module per panel
│       ├── models/     Qt item models (moves, variations, findings, notebook)
│       └── presets/    layout presets + schema
├── tests/  unit/ · property/ · differential/ · golden/ · ui/ · chaos/ · fuzz/
│           ml/ (inference, datasets, gates)
├── benchmarks/  (includes inference latency and batch throughput)
├── models/  registry.toml · downloaded artifacts (git-ignored)
└── assets/  pieces/ · icons/ · fonts/ · themes/ (20 packs) · board_palettes/
            samples/ · models/examples/
```

**Mirroring rule:** `tests/unit/<path>/test_<module>.py` mirrors
`src/chess_observatory/<path>/<module>.py`.

---

## 6. The DRY Backbone

Sixteen contracts. Build them early; every feature attaches to one.

### 6.1 Feature Registry (the spine)

```
Feature(
  id="pawn.isolated.count.v1",
  category=PAWN, unit=COUNT, per_side=True,
  compute=isolated_pawns,          # (EvalContext) -> int | float | tuple
  higher_is_better=None,
  doc="Pawns with no friendly pawn on an adjacent file.",
  version=1,
)
```

Consumers: evaluator terms, Position DNA, similarity weights, autopsy event
detection, horizon trajectories, explanations, report tables, `docs/metrics.md`.
No metric may be computed anywhere else.

A test asserts every feature has: an id, version, doc, unit, category at least
one test, a `metrics.md` entry, and a symmetry test. Duplicate ids fail CI.

### 6.2 Attack Map

`core/attacks.py` returns, per square, the set of attackers (by side) and the
pieces that defend it, plus pins, checks, discovered-attack candidates, x-ray
through one blocker, and "safe to occupy" (SEE ≥ 0).

Consumers: legality, SEE, tactics, influence, king safety, graphs, microscope,
DNA tactical tension. It is memoised per `(zobrist, variant_key)`.

**Rule:** there is exactly one implementation of "what attacks this square".

### 6.3 Layer Contract (every visual)

```
Layer(name, kind=Scalar|Categorical|Edges|Marks|Polyline,
      values, scale, palette, legend, tooltip_fn)
```

Board overlays, heat maps, graph edges, horizon timelines, diff views, the
headless SVG figures in reports and the PDF renderer all consume `Layer`.
Adding a visualisation never touches the renderer.

### 6.4 Chart Contract

`ChartSpec(kind=line|area|stacked|radar|gauge|timeline|scatter, series,
axes, annotations, palette, legend)`. One chart renderer feeds screen, HTML,
and PDF. No panel paints its own chart from scratch.

### 6.5 AnalysisResult

```
AnalysisResult(analyzer_id, version, position_key, params_hash,
               payload, layers, findings, metrics, failures,
               effort_used, elapsed_ms, cache_hit, reproducibility,
               trust,            # EXACT | DERIVED | LEARNED | NARRATIVE
               model_id)         # set only when trust == LEARNED
```

One serializer decides JSON shape. `reproducibility` records seeds, engine
ids/versions, parameter hashes, and model hashes — enough to replay the
analysis exactly, or to explain why a replay differs.

### 6.6 Effort Profiles

`analysis/effort.py`: `EffortProfile(name, per_analyzer_budget_ms,
global_deadline_ms, search_limits, allow_deepening, skip_policy)`.

Built-in profiles: `Quick` (1 s), `Standard` (10 s), `Deep` (60 s),
`Exhaustive` (unbounded, cancellable), `Proof` (verified results only).
Every analysis reports **which analyzers were skipped and why** — silence is
never allowed to look like completeness.

### 6.7 JobRunner

Every long operation has `progress`, `cancel`, `partial`. Progress is throttled
(≤ 20 updates/s). Cancellation is cooperative and leaves no orphan processes.

### 6.8 Engine Registry

`uci/registry.py` — one `EngineSpec` per engine: id, display name, license,
homepage, binary name patterns, protocol quirks, default options, strength
class, behavioral tags (`deterministic`, `neural`, `supports_multipv`,
`slow_stop`). The UI engine picker, CLI flags, config, and license notices are
all generated from this one table.

### 6.9 Services

```
open_game / save_game / current_game / make_move / undo / legal_moves
analyze(position, modules, effort, params, progress)
run_search(position, engine_id, limits)
compare(a, b) / diff_analyses(a, b)
apply_edit(position, EditSpec) / run_scenario_matrix
find_similar(position, k)
probe_tablebase(position) / verify_proof(proof)
export_report(document, path, format)
run_experiment(spec) / gauntlet(spec)
manage_engines(probe|install|list)
doctor() -> HealthReport
```

**Design rule:** every panel must be useful with `analyze(..., modules=())` —
i.e. no panel may require the conventional engine evaluation to show something
meaningful. That is the brainstorm's "useful even if you never touch engine
evaluation" requirement, made testable.

### 6.10 Reports: one document IR, three exporters

`reports/document.py` defines `ReportDocument(sections, figures, tables,
metadata, toc)`. `exporters/markdown.py`, `html.py` (self-contained, inline
SVG), and `pdf.py` (`QPdfWriter`) render it. Content generation never knows the
output format.

### 6.11 Design System

`ui/design/tokens.py` is the single source of colour, spacing, radius,
elevation, typography, motion. It generates the Qt stylesheet, the palette, the
chart colours, and the icon tint map. No literal hex code outside `tokens.py`
or a theme pack file. **20 theme packs** and independent board palettes are data,
not code (§10.2).

### 6.12 Corpus Abstraction

`store/corpus.py` presents games and positions identically whether they come
from SQLite, a Parquet shard, a PGN stream, or a test fixture. Similarity,
genealogy, archaeology, novelty, and book building all read through it.

### 6.13 Experiment Contract

`experiments/spec.py` — `ExperimentSpec(positions, engine_configs, limits,
metrics, repetitions, seed)`. Used by: engine A/B, SPRT, evaluator weight
comparison, search-parameter sweeps, "Analysis of Analysis" stability runs.
One runner, one stats module, one report shape.

### 6.14 Plugin API

`plugins/api.py` defines versioned entry points: `AnalyzerPlugin`,
`EnginePlugin`, `ModelPlugin` (custom inference backend), `ReportSectionPlugin`,
`ChartPlugin`, `ImporterPlugin`.
Manifest = TOML with `api_version`, permissions (`filesystem:read`,
`subprocess:engine`), and declared capabilities. Loader validates manifests,
runs conformance tests, isolates failures, and shows a permissions dialog on
first use.

### 6.15 Trust Labels

`core/trust.py` (no dependencies) defines the enum and the rules:
`EXACT > DERIVED > LEARNED > NARRATIVE` in evidential strength, but they are not
a ranking — they are different kinds of claim. Each output type declares its
label; `AnalysisResult.trust` is the *weakest* label among its contents unless
the contents are partitioned. UI badges, report legends, and the
`Verified only` filter are driven entirely by this field.

A test enumerates every `Finding` and `Metric` producer and asserts a label is
declared. There is no default.

### 6.16 Model Registry and Parity Gates

`ml/models/registry.py` — one entry per model artifact:

```
ModelSpec(id="eval.nnue.small", version="3", sha256=..., bytes=...,
          architecture="halfkp-256x2", inputs=Fingerprint spec,
          license="...", trained_on=DatasetRef(hash, license, games, plies),
          card="docs/models/eval-nnue-small-v3.md",
          determinism=Deterministic.CPU_ONLY,
          gates=GateReport(...), trust=LEARNED)
```

Rules:
- Model files are **optional downloads**, checksum-verified, never committed.
- A model is usable only if `gates` passes for the configured parity profile.
- `GateReport` records: accuracy vs search labels, Elo delta vs the classical
  evaluator in fixed-node self-play, calibration (ECE), CPU latency p50/p99,
  GPU latency, ablation (what happens when the network is removed), and the
  exact benchmark command.
- Deleting `models/` and setting `ml.enabled=false` must leave a fully working
  application — that is an enforced test, not a hope.

---

## 7. The Engine System (own engine: robust and tweakable)

This is the user-facing promise "how long to examine, and how". It is a
first-class subsystem, not a settings dialog.

### 7.1 Parameter registry

`search/params.py` declares every knob once, with metadata:

```
Param(name="multipv", type=int, default=1, min=1, max=32, step=1,
      tier=ParamTier.INTERMEDIATE, determinism=Deterministic.ALWAYS,
      restart_required=False, doc="Number of principal variations reported.")
```

Consequences, all automatic:
- CLI flags generated from the registry.
- UCI `setoption` names and types generated from the registry.
- Settings UI controls generated from metadata (slider/spin/combo/switch),
  grouped by `tier` (Basic / Intermediate / Expert / Experimental).
- `docs/search.md` generated from the registry.
- Config round-trip and migration tests generated from the registry.

`determinism` is per-param: `ALWAYS` (depth/nodes), `TIME_DEPENDENT` (movetime),
`HARDWARE_DEPENDENT` (threads). The UI shows a **Reproducible** badge when the
current configuration guarantees identical results.

### 7.2 Limits and time management

`SearchLimits(movetime_ms, wtime, btime, winc, binc, depth, nodes, mate,
infinite, multi_pv, soft_hard_ratio, move_overhead_ms, max_depth)`.

- Soft/hard deadline split, with deadline propagation from the analysis
  pipeline (an analyzer's budget becomes the search's hard ceiling).
- `move_overhead_ms` compensates for GUI/transport latency.
- Ponder support behind a flag (opt-in; disabled in analysis).
- Every search returns `SearchResult(score, bound, pv, depth, seldepth, nodes,
  nps, elapsed_ms, tt_stats, cutoff_stats, effort_used)`.

### 7.3 Search completeness (all behind toggles)

Aspiration windows, PVS, TT with buckets and aging, killers, history,
countermoves, IID, null-move, LMR, LMP, futility, razoring, SEE pruning, check
extension, singular extensions (experimental tier), qsearch with delta pruning,
mate-distance pruning, repetition/50-move/insufficient-material draws, MultiPV.

Each toggle is individually switchable so proof work can disable heuristics that
would compromise a claim.

### 7.4 Determinism modes

- `NodeDeterministic` — identical results across runs and machines (node limit).
- `TimeBest` — best move within a time budget (not byte-reproducible).
- `Proof` — deterministic, heuristics that break exactness disabled.

Recorded per analysis in `reproducibility`. Tests assert NodeDeterministic
produces identical PV/score/nodes in-process and across processes.

### 7.5 Parallelism, honestly

- Root splitting: each candidate move searched in a worker process; results
  merged deterministically at equal depth.
- Numba kernels (`nogil=True`) for eval/movegen hot loops where measured.
- No fake threading: a test asserts thread count changes do not silently
  degrade determinism guarantees.

### 7.6 Presets

Search presets (`Fast`, `Balanced`, `Deep`, `Proof`, `Analysis`, `Experiment`)
and analysis effort profiles (§6.6) are separate concepts and never conflated.

### 7.7 Engine Lab (experiments)

- `chess-obs experiment run spec.toml` — positions × configs × limits, N reps.
- Statistics: mean/median score, variance, Elo differences via logistic fit,
  SPRT for accept/reject, confidence intervals, per-position breakdown.
- Output: table + charts + reproducible TOML of the exact run.
- Used to validate every search change; results committed as
  `docs/experiments/NNNN-*.md`.

### 7.8 Learned guidance (optional, off by default)

When `ml.enabled` and a model is installed, search can consume two learned
signals, each individually switchable:

- **Policy prior** — replaces or blends with history/SEE ordering; measured by
  nodes-to-depth, not by vibes.
- **Neural evaluation** — used at leaf nodes, or as a *residual* on top of the
  classical decomposition (the residual is shown separately and labelled
  `LEARNED`, so the explanation never pretends to be complete).
- **MCTS mode** (experimental tier) — policy/value guided, with the same
  `SearchResult` shape and the same trace instrumentation.

Guarantees: classical ordering/eval remains available and is the default until
the parity gate passes; every learned run records `model_id` in
`reproducibility`; a missing or corrupt model degrades to the classical path with
a visible warning, never a crash. GPU inference is marked
`HW_DEPENDENT` for determinism purposes and is never used for `Proof` mode.

---

## 8. External Engine Federation

### 8.1 The promise

Adding an engine means editing one TOML file or dropping a binary on `PATH`.
Everything else — UI picker, CLI flags, comparisons, license notices,
tournaments — follows automatically.

### 8.2 Preconfigured engines (D10)

| Engine | Role | Notes |
|--------|------|-------|
| Stockfish | Reference strength | GPLv3, wide option surface, MultiPV |
| Berserk | Fast tactical reference | GPLv3 |
| Ethereal | Classical eval reference | GPLv3 |
| RubiChess | Strong classical reference | GPLv3 |
| Igel | Aggressive style contrast | GPLv3 |
| Lc0 | Neural reference | GPLv3 + network weights; first-class now that D7 allows learned references; flagged `neural`, results labelled `LEARNED` |
| *(opt-in)* Maia 1100–1900 | Human-likeness reference | Neural, trained on human games; used only for difficulty/human-style features (Phase 21) |

Rules:
- **Never bundle** engine binaries. Detect on `PATH`, read a config path, or
  offer `chess-obs engines install <id>` which fetches the official release,
  verifies a checksum, and shows license + source link before writing.
- Neural engines are marked in the registry (`kind=neural`, `needs_gpu`,
  `weights_license`) so the UI can show a GPU/weights notice and so consensus
  results can label them `LEARNED` rather than treating them as ground truth.
- Any engine can be added by the user; the registry is data, not code.
- A "no engines configured" state is fully functional (own engine only).

### 8.3 Adapter requirements

- Async subprocess client with strict timeouts, kill escalation
  (SIGTERM → SIGKILL), and automatic restart on crash.
- Capability probe: `uci` → `uciok` → enumerate options → `isready`, with
  per-engine quirk flags (`slow_stop`, `no_multipv`, `quoting`, `no_wdl`).
- Option mapping: our logical settings (threads, hash, multipv, syzygy path)
  map to each engine's real option names via `EngineSpec.option_map`.
- Result normalisation: score (cp/mate), PV, depth, seldepth, nodes, nps, time,
  hashfull, WDL when available.
- Sandboxing: absolute path only, no shell, no inherited CWD surprises,
  optional CPU/memory caps.

### 8.4 Multi-engine consensus

`uci/consensus.py` runs N engines under equal limits and reports:
- agreement rate on best move, rank correlation of PVs,
- disagreement cases with both lines and our own evaluator's verdict,
- a *consensus band* (min/max score) rather than a fake single truth.

Feeds "Analysis of Analysis" (item T, Phase 13) and the eval panel's reference
column.

### 8.5 Tournaments and gauntlets

`uci/tournament.py`: round-robin and gauntlet, opening-book-driven to avoid
repetition, fixed time or nodes, PGN output, Elo/SPRT stats via
`experiments/stats.py`, resumable (crash-safe state file).

### 8.6 Tests

`FakeEngine` variants covering: silent engine, wrong-name engine, missing
option, slow stop, crash mid-search, garbage info lines, huge PV, mate scores,
UTF-8 names. Every quirk flag has a fixture proving the adapter copes.

---

## 9. Data: Store, Corpora, ECO, Opening Book

### 9.1 Storage

- SQLite (WAL) for positions, games, analyses cache, notebooks, reports
  metadata, book stats, **datasets, models, training runs, gate reports**;
  forward-only migrations with tests.
- Parquet (memory-mapped float32 columns) for corpus-scale vectors and dataset
  shards; similarity and training scans never touch SQLite row-by-row.
- Model artifacts live in `models/` (git-ignored), addressed by sha256 and
  described by the registry; the database stores only references.
- Integrity: `PRAGMA integrity_check` on demand, checksummed backups,
  transactional imports, resumable jobs, disk-space preflight.

### 9.2 PGN import

Any legal PGN: streaming, resumable, dedupe by (zobrist, ply), tolerant of
missing headers, encoding detection, invalid-move reporting per game (never
abort the batch), progress + cancel. Ships one small sample corpus
(openly licensed) — never a dump.

### 9.3 ECO

`opening/eco.py` — ECO code + name + representative line, from an openly
licensed dataset (CC0-class; license recorded in `assets/`). Matched by move
sequence with fallback to longest-prefix; shown in the game panel, book panel,
autopsy, genealogy, and reports.

### 9.4 Opening book

- **Own format** `COB` (Chess Observatory Book): zobrist trie with move
  weights, comments, provenance, version, checksum; writer + reader +
  validator.
- **Polyglot `.bin` reader** (read-only) for the large existing ecosystem.
  Implemented against the published spec with byte-level tests; note that
  Polyglot uses its own zobrist scheme, verified with known test positions.
- **Book builder**: corpus → book with weighting (win rate, frequency),
  minimum-game filters, pruning thresholds; progress/cancel.
- **Book statistics**: per-line win rates, transposition merging, "book exit"
  detection; used by the Novelty Detector and Autopsy.
- Book play is available but **disabled by default in analysis** so results
  stay explainable.
- Book play stays **statistical**: corpus win rates plus Polyglot. A learned
  opening book is not planned for v1.0 (§3.5); the policy head is used for move
  ordering, not for book authoring.

### 9.5 Training data provenance

Every dataset that feeds a model has a manifest:

```
DatasetRef(id, sha256, created_at, source="pgn-import|self-play|engine-labels",
           license, games, positions, filters, generator_version)
```

- Datasets are built from openly licensed corpora or self-play; provenance is
  recorded per source and surfaced in the model card.
- Splits are deterministic and stored, so a val/test position can never leak
  into training (tested: hash intersection must be empty).
- Deletion is supported: removing a dataset marks dependent models as
  `orphaned` in the registry rather than silently keeping them usable.
- Nothing is uploaded. Training is local and offline.

---

## 10. Interface: A Scientific Instrument

Beauty is a requirement, not decoration. The target is "expensive laboratory
software": calm, dense, precise, dark by default, with deliberate motion.

### 10.1 Design system

**Tokens** (single source: `ui/design/tokens.py`)

| Token group | Values |
|-------------|--------|
| Surfaces (dark) | base `#0B0E13`, surface `#121722`, elevated `#182030`, overlay `#1E2739`, border `#232C3D` |
| Text | primary `#E6EAF2`, secondary `#9AA6BD`, muted `#6B7689`, inverse `#0B0E13` |
| Accents | primary `#4CC2FF` (cyan), secondary `#FFB454` (amber), success `#3DDC97`, warning `#FFC857`, danger `#FF5C7A`, info `#7AA2FF` |
| Light theme | surface `#FFFFFF`, base `#F7F8FA`, text `#161A22`, accent `#0A7EA4` |
| Spacing | 4-pt grid: 4, 8, 12, 16, 24, 32, 48 |
| Radius | 4 (controls), 8 (cards), 12 (panels), 999 (chips) |
| Elevation | 3 levels: hairline border, 1 px shadow, 2 px ambient |
| Typography | Inter (OFL) 11/12/13/15/20/28 px; JetBrains Mono (OFL) for numbers, nodes, FEN, engine output |
| Motion | 120 ms micro, 200 ms panel, 280 ms layout; ease `cubic-bezier(0.2, 0, 0, 1)`; disable-able |

**Rules**
- No stock Qt look: every interactive control is styled, including menus,
  tabs, scrollbars, splitter handles, tooltips, and dialogs.
- Density modes: `Comfortable` and `Compact` (row heights 32 / 26 px).
- No literal colour outside `tokens.py` or a theme pack (§10.2).
- Every chart colour sequence is colourblind-checked; heat maps default to
  cividis, with a diverging blue↔red mode for net influence.

### 10.2 Theme packs (20 shipped, unlimited user themes)

A theme is **data**, not code: a TOML pack that supplies token overrides and
declares its variant, license, and board palette. Packs may inherit from a base
(`based_on`), so a new theme is often 20 lines.

**Shipped set (20)**

| # | Theme | Variant | Character |
|---|-------|---------|-----------|
| 1 | Observatory Dark | dark | default; deep slate, cyan accent |
| 2 | Midnight | dark | navy/indigo, violet accent |
| 3 | Carbon | dark | neutral greys, minimal chroma |
| 4 | Slate | dark | blue-grey, muted, long-session calm |
| 5 | Nord | dark | arctic blue, cool neutrals (MIT) |
| 6 | Gruvbox Dark | dark | warm earth tones (MIT) |
| 7 | Solarized Dark | dark | teal/amber, low contrast (MIT) |
| 8 | Tokyo Night | dark | indigo/neon (MIT) |
| 9 | Catppuccin Mocha | dark | soft pastels (MIT) |
| 10 | Everforest | dark | forest green, warm (MIT) |
| 11 | Kanagawa | dark | ink and wave (MIT) |
| 12 | Amber Terminal | dark | monochrome amber, instrument feel |
| 13 | Parchment | light | warm paper, serif-friendly |
| 14 | Observatory Light | light | cool white, cyan accent |
| 15 | Solarized Light | light | low-glare paper (MIT) |
| 16 | Catppuccin Latte | light | soft pastel light (MIT) |
| 17 | GitHub Light | light | neutral, familiar (MIT) |
| 18 | Blueprint | light | white + blueprint blue grid accents |
| 19 | High Contrast Dark | a11y | `#000`/`#FFF` + strong accents, 7:1 targets |
| 20 | Deuteranopia Safe | a11y | neutral surfaces, blue/orange encoding only |

**Board palettes (independent of theme, 10)**: Classic Green, Walnut, Rosewood,
Marble, Slate, Ice, Blueprint, Paper, Monochrome, High Contrast. Any theme
combines with any palette (400 combinations), because board colours are their
own token group.

**Theme system behaviour**
- Instant switching at runtime, no restart; remembered per layout preset.
- Theme browser with live preview tiles; search and filter by variant.
- Custom theme editor with import/export TOML, plus a user themes directory.
- Print/PDF palette mapping: dark themes map to a print-safe light variant so
  reports are never dark-on-dark.
- `chess-obs themes list|validate|export`.

**Validation (automated, all 20)**
- Required-token completeness (missing key = build failure).
- Contrast: body text ≥ 4.5:1, large text/UI borders ≥ 3:1; a11y themes ≥ 7:1.
- Semantic distinctness: accent/warning/danger distinguishable under simulated
  deuteranopia and tritanopia (pure-Python simulation in tests).
- Chart sequence length and monotone lightness for heat-map ramps.

### 10.3 Component library (built once, used everywhere)

Button (4 variants × 5 states), icon button, segmented control, tabs, chip,
badge, **trust badge**, slider with value bubble, spin box, combo box, toggle
switch, search field, toolbar, breadcrumb, card, stat tile, divider, tooltip,
toast, inline alert, empty state, skeleton loader, progress bar (determinate +
indeterminate), table (striped, sortable, virtualised), tree, split handle,
context menu, dialog frame, command palette.

Each component: one module, token-driven, keyboard-accessible, and covered by a
pytest-qt test. No panel may hand-roll a control that exists in the library.

### 10.4 Board rendering

Custom `BoardWidget` on `QPainter` (no QGraphicsScene):

- Board pixmap cached per size/palette; dirty-region repaint only.
- Piece sets: two vetted CC0/MIT sets bundled with attribution, plus
  user-provided sets from the assets directory with license metadata.
- Coordinates, rank/file labels, turn indicator, move-number gutter.
- Overlays from `Layer`: legal-move dots, last-move tint, check pulse (one
  480 ms pulse, never looping), arrows (rounded shaft, 14 px head, 75 % alpha),
  heat maps (max 35 % opacity + legend), piece badges (pin, overloaded,
  hanging), diff tints (added/removed/weakened).
- Trust badges on evaluated overlays: a learned heat map is visibly marked, so
  a model output is never mistaken for a measured one.
- Interactions: click-to-move, drag with spring-back, promotion picker,
  keyboard move entry, right-click annotations (arrows, circles) that persist
  in the notebook.
- 60 fps target during drag; assert no full-board repaint on hover.

### 10.5 Charts and graphs

- `ui/charts/` implements line, area, stacked bar, radar, gauge, timeline,
  sparkline, and heat legend from `ChartSpec` (§6.4).
- `ui/charts/graphview.py`: deterministic force-directed layout
  (Fruchterman–Reingold with fixed seed), level-of-detail, edge bundling for
  dense graphs, focus+context, minimap, smooth zoom/pan, node pinning.
  Layout algorithms live in `graphs/layout.py` (tested, no `networkx` at
  runtime).
- The search-tree explorer reuses the same graph view with a different layout
  strategy and node decorators.

### 10.6 Workspace

- QMainWindow with docks; panel registry declares id, title, default area,
  min size; `View` menu is generated, never hardcoded.
- Presets: `Simple`, `Research`, `Tactics`, `Compare`, `Endgame`, `Observatory`,
  `Learning`; JSON layouts in the config dir, versioned, with corrupt-layout
  recovery. A preset also stores its theme, board palette, and density.
- Command palette (`Ctrl+K`) over all actions, panels, and analyses.
- Full-screen modes: `Tactics` (large board + motif list + variation strip) and
  `Presentation` (board + minimal eval, for showing someone a position).
- Session autosave: window state, current game, open boards, notebook, panel
  layout, theme — restored after a crash.

### 10.7 Motion and feedback

Motion is used only to explain change: piece slide, PV highlight sweep,
panel fade-in on first analysis, chart draw-in on new data, progress shimmer.
Every animation respects `ui.motion.enabled = false`. Data is never hidden
behind an animation: the final state is always reachable instantly.

### 10.8 Visual QA

Golden matrix (deliberately bounded so it stays maintainable):

| Coverage | Themes | Screens | Images |
|----------|--------|---------|--------|
| Full | 4 canonical (Observatory Dark, Parchment, High Contrast, Carbon) | every panel + both full-screen modes | ~60 at 1x/2x |
| Representative | all 20 | board + eval, graph, PDF page | 60 at 1x |
| Structural (not pixel) | all 20 | token completeness, contrast, palette math | unit tests |

- `QT_QPA_PLATFORM=offscreen`, fixed fonts and DPI, so images are stable.
- `chess-obs ui --screenshot <panel> --theme <id> --out file.png` for headless
  review.
- `docs/gallery/` holds the approved reference set; it changes only when a
  visual change is intentional and reviewed.
- Manual checklist per release: X11, Wayland, fractional scaling, font fallback,
  long text truncation, empty states, 250 % zoom, every theme's focus ring.

---

## 11. Reports: Markdown, HTML, PDF

`ReportDocument` (§6.10) with sections: Summary, Trust Legend, Evaluation
Story, Decomposition, DNA, Geometry/Influence, Tactical Events, Graph Analysis,
Counterfactuals, Horizon, Complexity/Criticality, Tablebase/Proof, Learned
Analysis (only when models were used), Autopsy Timeline, Similar Positions,
Model Cards, Bibliography of Methods.

- Every figure and table carries its trust label; the legend explains all four
  labels in one page.
- `LEARNED` sections always state model id, version, hash, and the gate report
  that allowed it into the product.
- The assistant's prose (if used) appears in a clearly marked `NARRATIVE` block
  with citations to the findings it summarises.

- **Markdown**: clean, version-controllable.
- **HTML**: single self-contained file, inline SVG boards and charts, no
  external URLs, print stylesheet.
- **PDF** via `QPdfWriter` from the first reporting phase: paginated layout
  engine (A4 + Letter), margins, running header/footer, page numbers, TOC,
  figures with captions, tables that split across pages correctly, embedded
  fonts (Inter + JetBrains Mono subsets).
- Determinism: identical input → identical page images. Because PDFs embed
  timestamps, tests compare **rendered page images**, not bytes.
- PDF is available from every panel's "Export" action, and via CLI.

---

## 12. Performance Doctrine

### 12.1 Sequence, not heroics

1. Correct pure Python. 2. Benchmark. 3. Profile (`cProfile`, `py-spy`).
4. Fix the data structure. 5. Only then consider a kernel.

### 12.2 Kernel boundary

Hot paths — movegen loops, attack tables, SEE, per-node eval increments,
influence diffusion, retrograde passes, batch feature extraction, distance
scans — live behind plain functions over primitives in `kernels/`.
Backend order: `numba_k` → `numpy_k` → `pure`. CI runs the whole suite with
`NUMBA_DISABLE_JIT=1`.

### 12.3 numpy rules

- Per-position 64-element vectors: **measure before using numpy**; call
  overhead usually loses to a plain loop. Use tuples/`bytes`/preallocated
  buffers.
- Batch work: numpy always (corpus features, distance matrices, retrograde,
  statistics).
- No allocation in per-node loops. `float32` for storage, `float64` for
  accumulation.

### 12.4 numba rules

Only in `kernels/numba_k.py`; `njit(cache=True)`, arrays only, pure functions,
never on the import path (extra `[jit]`), parity-tested against `pure.py`, with
an explicit CI leg proving the fallback works.

### 12.5 Budgets (calibrate after Phase 2, fail CI on > 20 % regression)

| Path | Initial target |
|------|----------------|
| Legal movegen | ≥ 150k positions/s |
| make/unmake | ≥ 500k ops/s |
| Search throughput | ≥ 40k nps |
| Eval call | ≥ 200k/s |
| DNA for one position | ≤ 25 ms |
| Influence map | ≤ 5 ms |
| Attack map | ≤ 3 ms |
| Full `Standard` analysis (cached warm) | ≤ 400 ms |
| Corpus DNA scan | ≥ 20k positions/s |
| Similarity query, 1M positions | ≤ 1 s |
| Similarity query, 10M positions | ≤ 3 s |
| Neural inference, small net, CPU p50 | ≤ 2 ms/position |
| Neural inference, batched corpus scan | ≥ 20k positions/s (CPU) |
| Model load (cold) | ≤ 500 ms |
| Training smoke test (CI, tiny dataset) | ≤ 60 s |
| Board redraw | ≤ 16 ms |
| Panel update (cached) | ≤ 100 ms |
| PDF export, 40-page report | ≤ 5 s |
| Cold start to interactive window | ≤ 1.5 s |

---

## 13. Engineering Standards

### 13.1 Standard of Done (every step)

1. `mypy --strict` clean for touched modules.
2. New behaviour has tests; bug fixes begin with a failing test.
3. `ruff check` + `ruff format` clean.
4. Public docstrings (Google style); new metric in `docs/metrics.md`;
   new parameter in `docs/search.md`; new panel in `docs/user/`.
5. No TODO without an issue reference; no commented-out code; no dead code.
6. Hot-path changes include a benchmark and a recorded number.
7. Visual changes include updated golden screenshots for every affected theme.
8. Learned outputs declare `trust`, `model_id`, and update the model card if
   numbers changed.

### 13.2 Typing and data modelling

- `from __future__ import annotations`; frozen dataclasses with `slots=True` for
  cross-module values.
- `NewType` for `Square`, `ZobristKey`, `CpScore`, `MoveInt`.
- Enums instead of magic ints in public APIs.
- Immutable snapshots outside `core`/`search`.

### 13.3 Naming

- Metric ids: `family.metric.qualifier.vN` (`pawn.isolated.count.v1`).
- Analyzers: `dna`, `geometry.influence`, `tactics.motifs`, `horizon`,
  `labs.entropy`.
- Engine ids: lowercase, stable (`stockfish`, `berserk`, `own`).
- Tests read as sentences.

### 13.4 Errors

```
ChessObservatoryError
├── CoreError → IllegalMoveError · InvalidFenError · InvalidPgnError
│               InvalidPositionError
├── AnalysisError → AnalyzerFailure · BudgetExceededError · CanceledError
├── EngineError → EngineNotFoundError · EngineTimeoutError · EngineCrashError
│                 EngineProtocolError
├── StorageError → CorruptIndexError · MigrationError
├── BookError · TablebaseError · ProofError
├── MLError → ModelNotFoundError · ModelIntegrityError · GateFailedError
│             InferenceError · DeviceUnavailableError
├── AssistantError → AssistantDisabledError · GroundingError
│                    ProviderTimeoutError
└── PluginError → PluginManifestError · PluginApiMismatchError
```

Never swallow silently. Every UI-visible failure states what failed and what to
do. An analyzer failure degrades to an error card in one panel, never a crash.

### 13.5 Config

One `Config` tree (dataclass), TOML at `~/.config/chess-observatory/`,
precedence CLI > env > user > defaults. Versioned with migrations. Zero-config
startup.

### 13.6 ADRs

`docs/adr/NNNN-title.md`. Required for D1–D21 and any architectural change:
0001 own core, 0002 hybrid federation, 0003 kernel boundary, 0004 feature
registry, 0005 AI/ML trust ladder, 0006 Linux-only, 0007 effort profiles, 0008
QtWidgets + design system, 0009 report IR, 0010 store split (SQLite +
Parquet), 0011 plugin API, 0012 determinism modes, 0013 book formats, 0014
threading/parallelism, 0015 image/asset licensing, 0016 visual QA, 0017 model
governance and parity gates, 0018 theme pack system, 0019 assistant grounding
and privacy, 0020 training reproducibility.

### 13.7 Git

Conventional Commits; one branch per phase; tag every milestone release.
Set `git config --global --add safe.directory "$PWD"` first (repo currently has
no commits).

### 13.8 Bootstrap script (`setup.sh`)

The first thing a new user runs, so it is held to the same standard as code.

**Contract**
- One command from the repo root; it locates itself, so the working directory
  does not matter.
- **Never** uses `sudo`, never edits system files, never deletes user data.
  Missing system libraries produce the exact package-manager command instead.
- Idempotent: running it twice is safe and fast.
- Network access only for `uv` installation, `uv sync`, and user-initiated
  model/engine downloads. No telemetry.
- Exit `0` = ready to launch; non-zero = a named problem with a fix printed.
- Ends by printing the launch command (`uv run chess-obs ui`) and the first-run
  notes (layout, theme, ML disabled by default).

**Modes**: `--check` (diagnose only), `--with-ml`, `--with-train`, `--with-gpu`,
`--with-ann`, `--all`, `--run`, `-y/--yes`, `-h/--help`.

**Verified by**: `bash -n`, `shellcheck`, a `--check` job in CI, and a container
smoke test from a clean Ubuntu image (no Python, no uv) that must reach the
launch command.

---

## 14. Testing and Robustness Doctrine

### 14.1 Oracles

| Area | Oracle |
|------|--------|
| Legality, perft | published perft suite + `python-chess` differential |
| FEN/SAN/PGN | `python-chess` round-trip + hand-built edge cases + fuzz |
| Graph algorithms | `networkx` (test-only) on small graphs |
| Search | mate suites, tactical suites, PV legality, determinism |
| Multi-engine adapter | `FakeEngine` quirk fixtures |
| Tablebases | published theory + independent search + internal consistency |
| Proofs | independent verifier + tamper tests |
| Eval/DNA | hand-computed fixtures, mirror invariance, goldens |
| Book (Polyglot) | published test positions + byte-level round-trip |
| PDF/HTML | rendered page-image goldens |
| Model outputs | golden inference fixtures + gate reports (§6.16) |
| Assistant text | grounded-fact bundle + stub-provider goldens |
| UI | pytest-qt + screenshot goldens |

### 14.2 Layers

| Layer | Content | Gate |
|-------|---------|------|
| Unit | every module | 95 % branch in `core`, `search`, `eval`, `analysis`; 90 % elsewhere |
| Property (hypothesis) | make/unmake, Zobrist, FEN/SAN/PGN round-trip, mirror invariance, legality of edits | zero failures at 2k cases in CI |
| Differential | vs `python-chess`, 100k games locally / 2k in CI | zero mismatches |
| Golden | metrics, reports, screenshots, PDF pages | reviewed updates only |
| Chaos | kill jobs, hang engines, corrupt DB/preset, full disk, unreadable assets | no data loss; recovery path proven |
| Fuzz | FEN/SAN/PGN/UCI lines/book/tablebase readers | no unexpected exception types |
| Soak | 2-hour scripted session, 200 games | no leaks, no growth in RSS beyond cap |
| UI | every panel, canonical themes, both DPIs | smoke + one interaction each |
| Themes | all 20 packs | token, contrast, colourblind, representative-screenshot goldens |
| ML | see §14.4 | every row in the ML table is a gate |

CI legs: `pytest` (fast), `--slow`, `NUMBA_DISABLE_JIT=1`, `--fuzz`, benchmark
compare vs `baseline.json`, import-graph guard, docs-freshness guard.

### 14.3 Robustness requirements (non-negotiable)

- **Watchdogs**: every engine call and every job has a hard timeout; kill
  escalation on shutdown.
- **Crash recovery**: session autosave every 10 s and on every mutation;
  restore on launch; journal file removed only after a clean exit.
- **Transactional data**: imports are resumable and idempotent; a killed import
  never leaves a half-written position row.
- **Graceful degradation**: any single analyzer, engine, or plugin can fail
  without taking down the workspace; failure surfaces as a dismissible card
  with the reason.
- **Diagnostics**: `chess-obs doctor` checks Python/deps, engine binaries,
  data files, DB integrity, asset licenses, disk space, and runs a 20-position
  sanity suite; `Export diagnostic bundle` produces a redacted report for bug
  reports (no PII, local only).
- **Reproducibility**: every analysis stores versions, params, engine ids and
  versions, seeds, and a replay command.

### 14.4 Machine-learning tests

Nothing learned ships on trust. Each item below is a gate, not a suggestion.

| Test | What it proves |
|------|----------------|
| Encoding round-trip | `decode(encode(p)) == p` for piece planes, history, castling, ep, side |
| Encoding invariance | colour mirror + 180° rotation map inputs/indices consistently |
| Dataset leakage | train/val/test position-hash intersection is empty |
| Dataset reproducibility | same sources + filters + seed → same manifest hash |
| Model integrity | sha256 mismatch refuses to load, with a clear error |
| Golden inference | fixed positions → outputs within tolerance; CPU path exact-ish (±1e-5) |
| CPU/GPU parity | agreement ≥ 99.9 % on move choice over 10k positions; documented tolerance |
| Calibration | ECE reported in the model card; gate fails above the configured bound |
| Latency | p50/p99 within the §12 budget on the reference machine |
| Ablation | removing the model returns to the classical path with no crash and no silent behaviour change |
| Missing model | `ml.enabled=true` with no artifact → visible warning + classical fallback |
| Gate report | every shipped model has a `GateReport` that passes the active profile |
| Assistant grounding | prompts can only cite facts present in the `AnalysisResult`; injected fabricated numbers are rejected by the renderer |
| Assistant offline | with no provider configured, every assistant entry point is disabled cleanly |

Training code is covered only by a **smoke** test (tiny dataset, 1 epoch) plus
unit tests for loss/shape/seed logic; full training is never CI work.

---

## 15. Phases

---

### Phase 0 — Foundations and Guardrails
*4–5 days · Gate: Linux CI green on a real (empty) project; `./setup.sh --check` diagnoses a clean machine correctly*

> **Status: complete (2026-11-23).** Evidence: `ruff`, `ruff format --check`,
> `mypy` (strict), and `pytest` all green (80 passed, 1 intentional skip);
> `chess-obs doctor` exits 0; `chess-obs ui --smoke` opens and closes the window
> offscreen; `tools/check_docs.py` validates 31 documents and 20 ADRs;
> `./setup.sh --check` and `./setup.sh` both succeed. CI runs every job below on
> a clean Ubuntu runner. Phase 1 is next.

1. Repo hygiene: `safe.directory`, `.gitattributes` (LF), initial commit.
2. `uv init --lib`, `src/` layout, pyproject (hatchling), version from package.
3. **`setup.sh`** — the single entry point for a fresh machine, shipped in this
   phase and treated as product code:
   - Detects Linux, Python ≥ 3.14, `uv`, the Qt/X11/Wayland runtime libraries,
     the display server, and optional GPU; prints the exact `sudo` command for
     anything it may not install itself.
   - Installs `uv` on request, then runs `uv sync` with the chosen extras
     (`[ml]`, `[train]`, `[gpu]`, `[ann]`).
   - Verifies the environment by importing the package and running
     `chess-obs doctor`; degrades gracefully while those do not exist yet.
   - Modes: `--check` (diagnose only), `--with-*`, `--all`, `--run`, `-y`.
   - Idempotent, no `sudo`, no system edits, no data deletion; every failure
     names the problem and the fix. Ends by printing
     `uv run chess-obs ui` — the command that opens the workspace.
   - Tested by `bash -n`, `shellcheck`, a `--check` run in CI, and a container
     smoke test from a clean image.
4. Asset licensing ledger (`assets/LICENSES.md`) — pieces, icons, fonts, the 20
   theme packs and their upstream palettes, ECO data, sample PGNs, and (later)
   model weights. CI fails on an unlisted asset.
5. Dependencies — runtime: `pyside6>=6.12`, `numpy>=2.3`, `pyarrow>=17`
   (Parquet corpus shards); optional `[jit]`: `numba>=0.68`; `[dev]`: pytest,
   pytest-qt, pytest-benchmark, pytest-cov, pytest-xdist, hypothesis,
   python-chess, networkx, ruff, mypy, pre-commit, pyinstaller.
6. Tooling: ruff (100 cols, isort, bugbear, pyupgrade), mypy strict, pytest
   markers (`slow`, `ui`, `bench`, `fuzz`, `chaos`), `--strict-markers`.
7. Smoke tests: import package; open a `QMainWindow` offscreen; assert PySide6
   and numpy versions.
8. ADRs 0001–0020 stubs with real content for 0001–0005, 0017, 0018.
9. `errors.py`, `logging.py` (rotating file + console), `config.py`,
   `serialization.py` — small but real, with tests for precedence and
   round-trip.
10. CI: ubuntu-only; jobs: lint, mypy, unit, property, differential,
    ui(offscreen), bench-smoke, docs-freshness, import-graph, `shellcheck
    setup.sh`, and `NUMBA_DISABLE_JIT=1`.
11. Fixtures skeleton + `conftest.py` factories (`pos(fen)`, `game(pgn)`).
12. Import-graph guard tests (PySide6 only in `ui`, `python-chess`/`networkx`
    only in tests).

**Gate**: all CI jobs green; window opens offscreen; doctor runs; ADRs merged;
`./setup.sh` and `./setup.sh --check` both behave correctly on a clean machine.

---

### Phase 1 — Rules Core
*10–14 days · Gate: perft exact, zero differential mismatches*

1. `squares.py`: 0 = a1 … 63 = h8; file/rank helpers; masks; shifts;
   popcount/lsb/msb; edge masks; knight/king tables; ray tables; `BETWEEN`,
   `LINE` tables. Tests: table symmetry, edge safety, counts.
2. `pieces.py`: `Color`, `PieceType`, `Piece`, char maps, bitboard constants.
3. `moves.py`: packed 32-bit move, flags (capture, ep, castle, double push,
   promo), `MoveList` as `array('i')`, UCI conversion.
4. `position.py`: immutable snapshot — 12 piece bitboards + occupancy, mailbox
   `bytes(64)`, side, castling, ep, clocks, `strict` flag, `variant_note`;
   `piece_at`, `king_square`, `copy`.
5. `zobrist.py`: splitmix64 with fixed seed; `compute_key`; incremental xors.
   Property test: incremental == recompute over random games.
6. `attacks.py`: `attackers_to(square, occ)`, slider rays, and the **full
   `AttackMap`** — per-square attackers/defenders, absolute/relative pins with
   rays, checks, discovered-check candidates, x-ray through one blocker, and
   safe-to-occupy (SEE ≥ 0); memoised per `(zobrist, variant_key)`. It is built
   here, not later, because legality, SEE (Phase 2), evaluation (Phase 4) and
   every visual (Phase 8) depend on this single implementation. Tests:
   hand-built pin/check/battery positions.
7. `movegen.py`: all piece types, castling path/attack rules, en passant,
   promotions; legality filter via checkers + pin masks + king-danger mask.
8. `make.py`: make/unmake with compact undo records; every field updated
   incrementally; debug assertions re-validate the whole position.
9. `edits.py`: counterfactual primitives — `remove_piece`, `add_piece`,
   `relocate_piece`, `set_side`, `clear_castling`, `set_ep`, `null_move`,
   `swap_kings`; each returns `(Position, LegalityReport)` naming every rule
   violated. Non-strict positions must still generate legal moves sanely.
10. `fen.py`: strict parser with precise errors; permissive mode; emitter.
11. `san.py`: generation (with disambiguation) and parsing.
12. `pgn.py`: headers, comments, NAGs, nested RAV, results, clock/eval
    annotations, encoding handling; streaming reader.
13. `docs/position-api.md`: the public core API, documented and frozen for
    other modules.
14. Perft suite (standard positions, depths 1–6 behind `--slow`, exact counts).
15. Differential harness (2k games in CI, 100k locally) comparing legal moves,
    FEN, and terminal status vs `python-chess`.
16. Benchmarks: perft nps, make/unmake, attack map, SEE.
17. Performance pass 1; record `baseline.json`.

**Gate**: perft exact; zero differential mismatches; 95 % branch in `core/`.

---

### Phase 2 — The Own Engine (robust, tweakable)
*12–16 days · Gate: mate suite solved; determinism proven; parameters fully wired*

1. `params.py`: parameter registry with metadata (§7.1) + generated docs +
   round-trip tests.
2. `limits.py`: `SearchLimits`, deadline propagation, soft/hard split, move
   overhead.
3. `tt.py`: transposition table with buckets, bounds, aging, size cap;
   array-backed variant behind the same interface (measure both).
4. `ordering.py`: TT move, MVV-LVA, promotions, killers, history, countermove,
   SEE ordering.
5. `engine.py`: negamax/PVS, alpha-beta, PV extraction, mate scores,
   draws (repetition, 50-move, insufficient material), qsearch with delta
   pruning.
6. Extensions and pruning set (§7.3), each behind its own parameter, with
   defaults documented in `docs/search.md`.
7. Iterative deepening, aspiration windows, MultiPV, `SearchResult`.
8. `trace.py`: bounded `SearchTrace` — per-depth summary (nodes, cutoffs, TT
   hits, branching, PV changes, eval trajectory) + optional sampled nodes.
9. Cancellation: cooperative checks; hard deadline; no orphan work.
10. Determinism modes (§7.4) with tests in-process and cross-process.
11. `parallel.py`: root-splitting across processes; deterministic merge at
    equal depth; a test proving the merge is stable.
12. `uci/server.py`: expose our engine as UCI (parity with our parameter
    registry; `setoption` for every param).
13. `presets.py`: Fast/Balanced/Deep/Proof/Analysis/Experiment.
14. Mate suites (in 1–3 full, curated in 4–5), tactical suite (≥ 300 labelled
    positions) with documented thresholds.
15. Stress: 10k random positions at depth 6 — no exceptions, PV legal
    move-by-move.
16. Benchmarks: nps, depth/second, TT hit rate, eval cost.
17. `docs/search.md` generated and reviewed.

**Gate**: mate suites 100 %; tactical threshold met; determinism tests pass;
10k stress clean; every parameter appears in CLI, UCI, UI metadata, and docs.

---

### Phase 3 — External Engine Federation
*8–12 days · Gate: 4 engines play a gauntlet unattended*

1. `uci/protocol.py`: line parsing, `info` normalisation, score/PV/WDL,
   encoding tolerance.
2. `uci/client.py`: async subprocess, handshake, capability probe, timeouts,
   kill escalation, auto-restart, stderr capture.
3. `uci/registry.py`: built-in `EngineSpec`s (§8.2) incl. license + homepage +
   option maps; user TOML extension; validation.
4. `uci/quirks.py`: per-engine flags + fixtures proving each is handled.
5. `uci/manager.py`: logical settings → engine options; probe/install/list;
   checksum-verified fetch on explicit user action; license + source display.
6. `uci/consensus.py`: N-engine runs, agreement metrics, disagreement report.
7. `uci/tournament.py`: round-robin + gauntlet, book-driven openings, fixed
   time/nodes, PGN output, resumable state, Elo/SPRT.
8. `experiments/`: `spec.py`, `runner.py`, `stats.py` (Elo, SPRT, CIs),
   `report.py` — shared by tournaments and parameter sweeps.
9. `FakeEngine` fixture set (§8.6) and a full adapter test matrix.
10. `chess-obs engines list|probe|install|bench`, `chess-obs gauntlet`.
11. UI data provider for the engine picker (used in Phase 6).

**Gate**: 4 preconfigured engines run a 200-game gauntlet unattended with a
crash-resume; every quirk fixture passes; no engine binary in the repo.

---

### Phase 4 — Feature Registry and Evaluation Decomposition
*12–16 days · Gate: decomposition accounting + mirror invariance pass*

1. `eval/registry.py`: `Feature`, `Category`, `Unit`, decorator registration,
   duplicate detection, ID/version rules, doc generation.
2. `EvalContext`: position + cached attack map + pawn hash + king zone + phase
   + lazy memo tables; one construction per analysis.
3. Feature families, each implemented once and tested:
   `material`, `mobility`, `space`, `king`, `pawn`, `control`, `coordination`,
   `tension`, `structure` (full list in `docs/metrics.md`).
4. `terms.py`: mg/eg tapered terms; each term names its feature(s).
5. `decomposition.py`: per-term and per-category contributions, white
   perspective and side-to-move perspective, **explicit** documented
   interaction terms instead of hidden cross-talk.
6. `presets.py`: `ClassicalEvaluator` (hand-set) and `ExperimentalEvaluator`
   (uncalibrated, purely mathematical) with identical breakdown shape.
7. `explain.py`: plain-language rendering from metadata only; used by UI, CLI,
   and reports.
8. Incremental evaluation for search: identify cheaply updatable features,
   measure the gain, keep only what pays.
9. Tests: hand-computed fixtures per family; mirror invariance for every
   feature; rank-flip symmetry where claimed; decomposition sum tolerance;
   monotonic sanity; NaN/inf exclusion.
10. `docs/metrics.md` generator + CI staleness check.

**Gate**: every feature documented and tested; decomposition accounting passes;
mirror invariance passes; goldens reviewed.

---

### Phase 5 — Analysis Framework, Jobs, Cache, CLI
*8–10 days · Gate: `chess-obs analyze` produces a real report from JSON*

1. `results.py`: `AnalysisResult`, `Finding`, `AnalysisFailure`, `Layer`,
   `WorkspaceAnalysis`.
2. `analyzer.py`: `Analyzer` protocol (`id`, `version`, `requires`,
   `params_model`, `run`), registry, conformance tests.
3. `pipeline.py`: DAG resolution, topological execution, per-analyzer failure
   isolation, incremental recompute.
4. `cache.py`: LRU keyed by `(id, version, zobrist, variant, params_hash)`;
   persistable interface; staleness/provenance metadata.
5. `jobs.py`: `Job`, `InlineRunner`, `ThreadRunner`, `ProcessRunner`,
   throttled progress, cancellation, partial results.
6. `effort.py`: profiles (§6.6), budget allocation, deadline propagation,
   skipped-analyzer reporting.
7. `render.py`: text/JSON/markdown renderers from `AnalysisResult` only.
8. `report_ir.py`: `ReportDocument` skeleton (fills in Phase 9+).
9. `services/` first slice: open/save game, move, legal moves, analyze, export.
10. `cli/`: command registry, `--format`, `--modules`, `--effort`, `--config`,
    exit codes (0 ok, 1 user error, 2 analysis failure, 3 internal bug), and a
    header block with versions, engine, effort, and reproducibility hash.
11. Tests: DAG order, failure isolation, cancellation at 50 %, cache
    invalidation, budget exhaustion, skipped-analyzer transparency, CLI
    golden output.

**Gate**: CLI produces text/JSON/markdown for a FEN; cancellation leaves no
orphans; every skipped analyzer is reported with a reason.

---

### Phase 6 — UI Foundation: Design System, Shell, Board
*16–22 days · Gate: designed, dockable, preset-driven workspace*

1. `design/tokens.py` → generated QSS + `QPalette` + chart palette + icon
   tints; density modes; the base token set that theme packs override.
2. `design/theme_packs/`: the **20 shipped themes** (§10.2) as TOML packs with
   inheritance, plus 10 board palettes; validator with token-completeness,
   contrast, and colourblind-simulation tests.
3. `design/theme.py`: runtime switching without restart; per-preset theme
   binding; theme browser with live preview tiles; custom theme editor with
   import/export; print/PDF palette mapping.
4. `design/motion.py`: animation primitives honouring the disable flag.
5. `components/`: the full library of §10.3, each with a showcase page and a
   pytest-qt test.
6. `ui/app.py`: bootstrap, HiDPI, font loading (bundled Inter/JetBrains Mono),
   global exception hook, splash, cold-start budget.
7. `bus.py`: typed signal bus; explicit injection.
8. `main_window.py`: docks, generated `View` menu, command palette, and the
   **Analysis bar** — effort-profile selector (Quick/Standard/Deep/Exhaustive/
   Proof), time-budget slider, engine selector(s), `Reproducible` badge,
   progress and cancel. Status bar shows engine, effort, cache, and the
   skipped-analyzer count.
9. Panel registry + `AnalysisPanel` base (busy/empty/error states, declared
   analyzer requirements, `min_refresh_ms`).
10. Presets with versioned JSON, save/restore, corrupt-layout recovery.
11. `board/`: `BoardWidget` + overlays + piece sets + drag/click + promotion +
    coordinates + cached pixmaps (§10.4).
12. `charts/`: the chart renderer + graph view (§10.5) with token styling.
13. `session.py`: autosave/restore of layout, files, notebook, boards.
14. Models: moves, variations, findings, notebook (`QAbstractItemModel`).
15. Visual QA harness: screenshot goldens (1x/2x, canonical themes), `--screenshot`
    CLI, gallery baseline; theme matrix from §10.8.
16. Accessibility pass: focus rings, tab order, accessible names, contrast
    audit.
17. First real panel: Evaluation (uses Phase 4 features even without search),
    proving the vertical slice end-to-end.

**Gate**: shell launches under 1.5 s; all 20 themes pass token/contrast/
colourblind validation; canonical-theme goldens match; presets (including their
theme and board palette) restore after restart; no GUI-thread block > 50 ms;
evaluation panel works with a bare FEN.

---

### Phase 7 — Position DNA
*7–9 days · Gate: `dna_v1` frozen; distance properties proven*

1. `dna/schema.py`: `Fingerprint(version, key, vector, categorical,
   structural_hashes)`; fixed dimension order declared by the schema.
2. Dimension list `dna_v1` (reviewed, explicit); adding a dimension bumps the
   version; stored with the vector.
3. Normalisation table: documented transforms (log1p, scaling, signed
   asymmetry); tests for monotonicity and totality (no NaN/inf).
4. `dna/compare.py`: distance registry — weighted L1/L2/cosine + categorical
   mismatch penalty; serialisable weights.
5. `dna/report.py`: DNA card (distinguishing dimensions vs a reference set),
   text/JSON via the shared renderer.
6. `dna/analyzer.py`: registers the `dna` analyzer; emits layers for
   per-dimension comparison.
7. UI: DNA panel — radar/bars, categorical chips, compare slot, "why this
   differs" sentences from `explain.py`.
8. Tests: determinism, mirror invariance, metric identities, goldens,
   "materially equal but structurally different" fixture pairs separate above
   a documented threshold.
9. CLI: `chess-obs dna --fen ... [--compare-fen ...]`.

**Gate**: `dna_v1` frozen and documented; property tests pass; panel matches
goldens.

---

### Phase 8 — Geometry, Influence, and the Microscope
*12–16 days · Gate: heat maps and microscope match hand-computed fixtures*

1. Harden the `AttackMap` built in Phase 1 against the full specification
   (§6.2): fuzz the pin/x-ray/discovered cases, verify SEE against a brute-force
   capture-resolution reference, and profile it. Any gaps found are fixed in
   `core/attacks.py`, not patched locally.
2. Prove there is exactly one attack implementation: an import/grep test that
   fails if any module computes attackers independently.
3. `geometry/influence.py`: influence density per square (weight ×
   conditionality × pinnability), white/black/net layers, cached per position.
4. `geometry/mobility.py`: bounded reachability BFS, knight distances,
   colour-complex asymmetry, trapped-piece detection.
5. `geometry/king.py`: king zone, escape classification, attack routes.
6. `geometry/layers.py`: everything as `Layer`s (heat, control, edges).
7. `geometry/microscope.py`: data providers for all six modes — piece, square,
   pawn, king safety, tactical, exchange.
8. UI: Geometry panel (layer selector, palette, scale, legend, hover values)
   and Microscope panel (piece/square click → attacks, defences, destinations,
   role, "if it moves/exchanged" with quick search).
9. Tests: hand-built positional fixtures (pinned knight, back-rank battery,
   overloaded queen, opposite-coloured bishops); influence sums conserved;
   `Layer` round-trip; performance on 1k positions.
10. Benchmarks: attack map, influence, reachability.

**Gate**: fixtures match numerically; single attack implementation proven;
panels match goldens; budgets met.

---

### Phase 9 — Attack/Defence Graph and Graph Analysis
*10–14 days · Gate: parity with `networkx` on 1,000 positions*

1. `graphs/build.py`: piece and square nodes; typed edges (`ATTACKS`,
   `DEFENDS`, `PINS`, `BLOCKS`, `THREATENS`, `DEPENDS_ON`); stable node ids for
   cross-position diffing.
2. `graphs/algorithms.py`: degree/betweenness centrality, articulation points,
   bounded min-cut sets, dependency closure, overloaded-defender detection,
   defensive-network robustness score.
3. `graphs/layout.py`: deterministic force-directed layout (seeded
   Fruchterman–Reingold), level-of-detail, edge bundling, node pinning.
4. `graphs/diff.py`: structural diff between two positions (added, removed,
   strengthened, weakened edges; node role changes).
5. `graphs/render_data.py`: `Layer`/`ChartSpec` output for the graph view and
   reports.
6. UI: Graph panel — interactive graph, focus+context, click node → board
   highlight, edge filters by type, "what breaks if this piece goes".
7. Report foundation: `ReportDocument` + markdown/HTML/**PDF (QPdfWriter)**
   renderers with the first sections (summary, eval decomposition, DNA,
   geometry, graph figures); export from every panel.
8. Tests: algorithm parity vs `networkx` on ≥ 1,000 random positions;
   determinism of layout; diff symmetry; PDF page-image goldens; HTML
   self-containment.
9. Benchmarks: build + algorithms + layout at 32 pieces.

**Gate**: parity and determinism pass; PDF export works and matches page
goldens; `v0.1.0` tagged after the Phase 9 gate review.

---

### Phase 10 — Tactical Universe
*12–16 days · Gate: motif suite precision ≥ 0.90, recall ≥ 0.75*

1. `tactics/motifs.py`: independent detectors over `AttackMap` + legal moves —
   fork/double attack, absolute/relative pin, skewer, discovered attack/check,
   deflection, decoy, clearance, interference, zwischenzug, back-rank, trapped
   piece, overloaded defender.
2. `Motif(kind, squares, pieces, severity, evidence)`; shared evidence format.
3. `tactics/dependencies.py`: duty resolution — "defends X, guards square Y,
   blocks Z", critical vs optional duties, the dependency chain narrative.
4. `tactics/latent.py`: motifs that appear after a preparatory move (top-K
   children of a shallow search), with the triggering move recorded.
5. `tactics/verify.py`: every reported combination verified by search to a
   configurable ply budget; unverifiable motifs demoted or dropped per
   strictness setting.
6. Labelled suite (≥ 120 positions) with positive and negative fixtures;
   thresholds enforced in CI.
7. UI: Tactics panel + board arrows + full-screen Tactics mode (large board,
   motif list, variation strip).
8. Tests: per-motif fixtures, negative fixtures, determinism, suite
   thresholds, performance on 1k positions.
9. Docs: every motif with an example and a counter-example.

**Gate**: thresholds met; Tactics mode usable; every motif documented.

---

### Phase 11 — Pawn Structure Research Engine
*8–10 days · Gate: transition graph correct on 20 reference structures*

1. `pawn/features.py` (registered features): islands, backward, isolated,
   doubled, hanging, passed/connected/protected/candidate, chains, breaks,
   majorities, weak squares, locked structures, lever squares.
2. `pawn/transition.py`: pawn-structure transition graph — nodes are pawn
   configurations, edges are pawn moves/captures; BFS for "moves to a passed
   pawn", "which break creates a permanent weakness".
3. `pawn/breaks.py`: break evaluation — does the break improve the structure,
   open a file, create a target; scored by explicit features.
4. `pawn/eval_terms.py`: structural terms reusing the same features (no
   duplication).
5. UI: Pawn panel — structure map, transition graph, break list with
   consequences; integrates with the graph view.
6. Tests: 20 reference structures with expected classifications; transition
   graph invariants (acyclic in pawn-count, edge legality); determinism.
7. Narrative sentences in `explain.py` for each pawn feature.

**Gate**: reference structures correct; transition graph usable in the UI.

---

### Phase 12 — Counterfactuals, Exchange Consequence Analyzer
*12–16 days · Gate: brainstorm's worked example reproduced; UI round-trip clean*

1. `counterfactual/spec.py`: `EditSpec` (remove/add/relocate piece, side to
   move, null move, castling rights, ep, swap kings) + `TurnPolicy` for
   double-move *analysis* (core still applies one move at a time).
2. `counterfactual/apply.py`: apply + `LegalityReport` + plain summary of what
   is now undefined.
3. `counterfactual/diff.py`: per-feature deltas, square-control changes,
   new/removed motifs, eval-delta decomposition, graph diff, mobility/king
   changes; emits "what changed" layers.
4. `counterfactual/scenarios.py`: named generators (exchange a piece, grant a
   tempo, advance a pawn, remove a defender, open a file).
5. `counterfactual/lab.py`: scenario matrix batch, ranked by impact.
6. `counterfactual/exchange.py`: Exchange Consequence Analyzer — material,
   structure, king safety, control, activity, files, tactics, endgame
   character; exchange tree over alternative capture sequences; comparison
   view.
7. UI: "What if…" panel (edit controls, validity warnings, side-by-side boards,
   diff heat map, revert), Exchange panel (tree + consequences), Position
   comparison mode.
8. Tests: edits never corrupt (property); validity reports correct; diff
   antisymmetry where meaningful; batch determinism; golden worked example
   ("remove Black's dark-squared bishop" → documented structural changes).
9. Benchmarks: 50-scenario matrix < 5 s.

**Gate**: worked example reproduces qualitatively; exchange tree matches
hand-checked lines; comparison mode matches goldens.

---

### Phase 13 — Horizon, Complexity, Criticality, Analysis of Analysis
*12–16 days · Gate: golden profiles reviewed; no NaN/inf anywhere*

1. `horizon/curve.py`: horizons 1/2/4/6/8/12 (configurable), per-feature
   trajectories, volatility, sampled positions along the PV.
2. `horizon/events.py`: irreversible commitments, permanent weaknesses, lost
   defenders, lost critical squares.
3. `complexity/metrics.py`: branching, tactical density, evaluation stability,
   strategic flexibility, forcing ratio, "many moves, few choices" classifier.
4. `criticality/metrics.py`: moves within tolerance, best↔second gap,
   single-defensive-resource flag, forced-win/draw preservation, uniqueness
   score — all from MultiPV where possible.
5. `analysis/of_analysis.py`: confidence profile — depth sensitivity, PV
   stability, MultiPV spread, classical vs experimental agreement, own engine
   vs reference-engine agreement. Explicitly **not** a probability.
6. UI: horizon timeline scrubber, complexity gauge with dimensions,
   criticality badges on the move list, confidence panel with explicit
   caveats.
7. Tests: determinism at fixed nodes; monotonicity sanity for complexity;
   criticality reproducibility; golden profiles for 10 positions; NaN/inf
   guards on every derived metric.

**Gate**: 10 goldens reviewed for plausibility; all four features render
without new panel-base code.

---

### Phase 14 — Store, Corpora, ECO, Opening Book
*12–16 days · Gate: 1M positions imported; book round-trips; ECO matches*

1. `store/schema.py` + migrations: positions, games, analyses, notebooks,
   reports, book stats; forward-only migrations with tests.
2. `store/bulk.py`: Parquet shards for vectors; memory-mapped float32 columns.
3. `store/import_pgn.py`: streaming, resumable, dedupe, tolerant parsing,
   per-game error report, progress/cancel.
4. `store/integrity.py` + `backup.py`: integrity check, checksummed backups,
   restore, corruption recovery.
5. `store/corpus.py`: the `Corpus` abstraction (§6.12) over SQLite, Parquet,
   PGN streams, and fixtures.
6. `opening/eco.py`: ECO table from an openly licensed dataset; longest-prefix
   matching; UI display in game/move panels.
7. `opening/book_format.py`: `COB` reader/writer/validator + checksums.
8. `opening/polyglot.py`: reader against the published spec; byte-level and
   known-position tests.
9. `opening/builder.py`: corpus → book with weighting, filters, pruning,
   progress.
10. `opening/stats.py`: per-line win rates, transposition merging, book-exit
    detection.
11. UI: Opening panel (ECO, book line, stats), import dialog with live error
    counts, corpus manager.
12. Sample corpus + one small sample book, both openly licensed.
13. Tests: migration upgrades, import resumability under kill -9, book
    round-trip, Polyglot fixtures, ECO matching edge cases, 1M-import benchmark
    and memory test.

**Gate**: 1M-position import completes with integrity check and bounded memory;
books validate; ECO matches reference.

---

### Phase 15 — Learning Infrastructure
*10–14 days · Gate: a tiny model trains reproducibly, loads through ONNX, and a bad artifact is refused*

1. `ml/encoding/`: board planes (12 piece planes + side, castling, ep, halfmove,
   repetition/history), perspective flipping, move index maps (from/to/promo)
   with legal-move masking. Tests: round-trip, colour-mirror and rotation
   invariance, index stability across versions.
2. `ml/datasets/`: builders from store corpora, self-play, and engine labels;
   manifests with sha256 + provenance + license; deterministic, stored splits;
   leakage and reproducibility tests.
3. `ml/training/`: config-driven loop — seeds, deterministic flags, checkpoint
   and resume, local metric logs (no telemetry), CPU/GPU, tiny-dataset smoke.
4. `ml/inference/`: `InferenceBackend` protocol; ONNX Runtime backend (CPU +
   optional CUDA/ROCm providers), warmup, bounded batch queue, thread safety,
   model load/unload, clear failure when the artifact or provider is missing.
5. `ml/models/`: registry, `registry.toml`, model-card schema, checksum
   verification, explicit user-initiated download, integrity errors (§6.16).
6. `ml/gates/`: `GateReport` runners — parity vs classical, calibration (ECE),
   latency p50/p99, ablation, CPU/GPU agreement — with named threshold profiles.
7. `ml/selfplay/`: generator over the own engine (MCTS arrives in Phase 17),
   labelling, storage, resumable.
8. Trust plumbing: `core/trust.py`, `trust` on findings/metrics, trust badge
   component, `Verified only` / `Hide learned` filters wired through services.
9. CLI: `chess-obs models list|verify|download|card`, `chess-obs datasets
   build`, `chess-obs train smoke|run`.
10. Config: `ml.enabled`, device, batch size, model overrides, per-model
    disable; full test suite runs green with `ml.enabled=false`.
11. Optional extras: `[ml]` (onnxruntime), `[train]` (torch), `[gpu]`.
12. Docs: `docs/models.md`, model-card template, training reproducibility guide.

**Gate**: two identical smoke trainings produce the same manifest and artifact
hash; ONNX loads and runs; a corrupted artifact is refused with
`ModelIntegrityError`; the whole suite passes with ML disabled.

---

### Phase 16 — Position Similarity and Comparison Workspace
*12–18 days · Gate: 1M-position query < 1 s, recall ≥ 0.99; embeddings optional*

1. `similarity/index.py`: `VectorIndex` protocol with `BruteForceIndex`
   (reference) and `BucketedIndex` (pawn hash → material signature → exact
   scan).
2. `similarity/embeddings.py`: a small self-supervised embedding model trained
   on corpus positions (Phase 15 infrastructure); exposes a `DistanceMetric`
   that is **additive** to the explicit-feature metrics, never a replacement.
3. `similarity/ann.py`: optional HNSW/faiss adapter behind the index protocol;
   exact fallback always available and used in tests as the oracle.
4. `similarity/query.py`: weighted multi-criteria queries (structure, king
   safety, mobility, tension, material, and optionally embedding distance) with
   per-dimension explanations of *why* each match ranked.
5. Transposition awareness: exact-key dedupe, transposition grouping.
6. UI: Similarity panel — query from the current position, thumbnails, "surprise
   me" (max distance), save as collection; open a result in a comparison board.
7. Multi-board comparison workspace scaffolding (two boards, linked navigation,
   shared overlays); expanded to N boards in Phase 20.
8. CLI: `chess-obs similar`, `chess-obs build-index`, `--metric features|embedding`.
9. Tests: bucketed vs brute-force equivalence (recall ≥ 0.99 of true top-k for
   k ≤ 100 on 100k vectors), embedding determinism, ANN vs exact agreement,
   1M benchmark, index rebuild and corruption recovery.

**Gate**: budget met; recall proven; embedding metric is clearly optional and
labelled `LEARNED`; comparison board matches goldens.

---

### Phase 17 — Learned Evaluation and Search Guidance
*14–20 days · Gate: one model passes the parity profile; ablation is clean*

1. `learned/eval_nn.py`: NNUE-style net with incremental accumulator updates
   (or a small CNN baseline where incremental updates are not feasible), input
   spec shared with `ml/encoding/`, CPU latency budget from §12.
2. Hybrid evaluation: classical terms **plus** a learned residual. The
   decomposition shows `learned.residual` as its own labelled term, with an
   ablation toggle that removes it and re-runs the same analysis for comparison.
3. `learned/policy.py`: policy head for move ordering; maps policy indices to
   legal moves, ignores illegal/missing entries without failing.
4. MCTS mode (experimental tier): PUCT using policy + value, same
   `SearchResult` shape and the same trace instrumentation; deterministic with
   node limits and a fixed seed on a single thread.
5. Training: supervised labels from deepening search + self-play; curriculum;
   checkpoint selection by gate metrics, not by loss alone.
6. Gates before any default change: Elo vs classical at fixed nodes, nodes-to-
   depth improvement, calibration, CPU latency, ablation, determinism envelope.
7. Registry integration: `eval.backend`, `policy.enabled`, `mcts.*`, `ml.device`
   appear automatically in CLI, UCI `setoption`, settings UI, and docs.
8. UCI server: expose eval backend, model id, and MCTS options so external tools
   and tournaments can test us.
9. UI: Model panel (installed models, cards, gate reports, device, latency,
   memory), eval panel shows the learned residual with a trust badge, and the
   settings page is generated from the parameter registry.
10. Experiments: every model change ships `docs/experiments/NNNN-*.md` with the
    gate report and ablation.
11. Tests: golden inference, incremental accumulator == full recompute, policy
    legality handling, determinism envelope, ablation fallback, latency p50/p99.

**Gate**: one model passes the parity profile on the reference machine; the
classical path is still the default until then; ablation clean; no silent
upgrade path exists (model id is in every reproducibility record).

---

### Phase 18 — Endgame Laboratory, Fortresses, Proofs
*20–26 days · Gate: 4-man tables verified; all tamper tests rejected*

1. `endgame/tb_format.py`: compact table format (header, metric DTM/DTZ,
   indexing scheme, version, checksum), bit-packed, memory-mapped reader;
   formal spec in `docs/tablebase-format.md`.
2. `endgame/retrograde.py`: generator for all ≤ 4-man configurations + selected
   5-man; iterative passes, symmetry reduction, progress/cancel, numba kernel
   with pure fallback.
3. Verification harness: published theory, independent search at increasing
   depth, internal consistency (win count vs winning moves).
4. `endgame/probe.py`: own TB + optional Syzygy adapter; WDL/DTM/DTZ, best-move
   classification, zugzwang detection, insufficient-material logic.
5. `endgame/fortress.py`: fortress candidates (structure patterns, blockade,
   opposite-coloured bishops, stalemate resources, perpetual check), plus
   learned candidate generation (Phase 17/21) — **every** candidate, derived or
   learned, is verified by bounded proof search before being claimed.
6. `endgame/explorer.py`: modify one piece → outcome delta table (uses Phase 12
   edits).
7. `proof/tree.py` + `proof/build.py`: AND/OR tree for forced mates/wins within
   a ply budget, pruned by tablebase knowledge.
8. `proof/verify.py`: independent verifier (no shared search code), returns
   `VerificationResult(valid, reason, depth, nodes_checked)`.
9. UI: Endgame panel (probe result, outcome explorer, fortress candidates),
   Proof panel (tree view + verify button).
10. Tests: proof round-trip; tamper tests (flip a move, drop a defence, claim a
    non-terminal) 100 % rejected; tablebase spot-checks (KQK, KRK, KBNK, KPK,
    KPKP); fortress claims verified or rejected with reasons; kill -9 resume.

**Gate**: 4-man tables generated and verified; tamper suite passes; proofs
reproducible from CLI.

---

### Phase 19 — Autopsy, Genealogy, Full Reports
*14–18 days · Gate: documented findings on 10 reference games*

1. `autopsy/events.py` + `rules.py`: per-ply pipeline and explicit,
   config-driven event rules — first structural mistake, flexibility loss,
   broken defensive relationship, surrendered critical square, first missed
   tactic, draw→hard transition, decisive transition.
2. Each event carries evidence (ply, feature deltas, motif, line).
3. `autopsy/narrative.py`: ordered reconstruction rendered by the shared
   renderer (no hand-written prose). Optional learned enrichment: difficulty per
   move and blunder-risk bands (Phase 21), always with confidence intervals and
   a `LEARNED` label.
4. `genealogy/cluster.py` + `families.py`: opening positions clustered by
   fingerprint (with an optional embedding distance from Phase 16, shown
   separately); families → resulting structures → typical endgames; queries
   like "which openings produce an IQP".
5. Report content: all sections of §11, with figures (boards, charts, graphs),
   captions, and the methods bibliography.
6. UI: Autopsy panel (game timeline, event markers on board and move list,
   click-to-jump), Genealogy panel (cluster map + drills).
7. Export: markdown, HTML, PDF from the same document, byte-identical page
   images across runs.
8. Tests: 10 reference games with expected events (golden, severity-tolerant);
   deterministic renders; 200-ply game completes < 60 s with progress; PDF
   pagination goldens (tables splitting, long captions).

**Gate**: reference findings reproduced; exports stable; timeline navigation
fluid.

---

### Phase 20 — Search Observatory, Workspace Modes, Notebook
*12–16 days · Gate: live and replayable search inspection works end-to-end*

1. Search trace pipeline: bounded in-memory trace + optional on-disk trace for
   replay; sampling policy documented.
2. `ui/panels/search_observatory.py`: live tree growth, node counts, cutoffs,
   TT hit rate, PV changes over time, branching factor, eval fluctuation,
   most-examined positions, time distribution; pause/resume/inspect.
3. Search-tree explorer: reuse graph view; depth layers, cutoff colouring,
   node detail panel (position, score, bounds, TT state).
4. Multi-board comparison workspace: N boards with synchronized navigation,
   linked overlays, diff mode between any two.
5. Analysis notebook: notes per position, saved arrows/circles, findings
   pinned, variations attached, export into reports; persisted in the store.
6. Full-screen Presentation mode.
7. Tests: trace replay determinism; observatory renders 1M-node trace within
   memory cap; multi-board synchronization; notebook round-trip; screenshot
   goldens for all modes.

**Gate**: observatory usable on a live 60-second search; all workspace modes
golden-tested.

---

### Phase 21 — Learned Perception Labs
*12–18 days · Gate: each lab passes calibration and refusal tests*

**Scope note:** the set is fixed. The motif classifier was adopted earlier; the
six labs approved on 2026-11-23 are difficulty, human-likeness, board-image
recognition, style profiling, puzzle generation, and blunder-risk prediction.
Learned book, coach mode, engine-assistance detection, and personal models are
**not built**. Nothing in this phase ships without a model card and a gate
report.

1. **Motif classifier** (`learned/motif_clf.py`): trained on auto-labelled
   motifs that were verified by search. Runs as a second opinion beside the
   derived detectors, ranked by confidence, never suppressing a derived motif.
2. **Difficulty estimation** (`learned/difficulty.py`): per-position difficulty
   from move uniqueness, complexity, and model signal; calibrated against a
   labelled puzzle set; shown with a confidence band.
3. **Human-likeness** (`learned/human_like.py`): optional Maia integration —
   "what a 1200/1600/2000 player most likely plays", clearly labelled
   `LEARNED` and never used for objective evaluation.
4. **Board-image recognition** (`learned/vision.py`): paste a screenshot or
   diagram, detect the grid and pieces, then require manual confirmation before
   the position is used. Failure is expected and handled gracefully.
5. **Player style profiling** (`learned/style.py`): embeddings over corpus games
   → style axes (aggression, solidity, tacticality, opening breadth) with
   per-axis evidence; compare two players.
6. **Puzzle generation** (`learned/puzzles.py`): positions with a unique winning
   line, calibrated difficulty, export to PGN/JSON; uniqueness verified by
   search, never assumed.
7. **Opening repertoire recommendation** (`learned/repertoire.py`): rank lines by
   style, level, and measured results; every recommendation shows the features
   and statistics behind it.
8. **Blunder-risk prediction** (`learned/blunder.py`): trained on human games;
   surfaced in the autopsy as a heuristic with an explicit confidence interval.
9. Tests: calibration, refusal cases, privacy (no uploads, paths redacted),
   provenance, and a hard rule that no lab can overwrite a derived finding.

**Gate**: every lab above has a model card, a gate report, a fixture set, and a
documented failure mode; the four dropped capabilities do not exist in the code.

---

### Phase 22 — Wild Labs A: Dynamics
*10–14 days · Gate: each lab produces verified, explainable output*

1. **Chess Entropy**: distribution of outcomes over a bounded sample of
   continuations; constrained-freedom measure; entropy curves vs depth.
2. **Sacrifice Laboratory**: systematic sacrifice search (material given for
   initiative/king exposure/long-term recovery), verified by search, ranked by
   compensation components.
3. **Forced Move Detector**: practical freedom — moves that do not lose
   immediately, moves that preserve the evaluation, near-forced positions with
   many legal moves.
4. **King Safety Simulator**: enumerate attack routes against a king, defensive
   resources at each stage, "how many attackers can arrive by ply N".
5. UI: `Labs` workspace with one panel per lab, shared controls, all results
   as layers/charts, all claims search-verified.
6. Tests: hand-checked fixtures per lab; determinism; performance caps;
   explanations generated from metadata.

**Gate**: each lab has a documented example, a counter-example, and a golden.

---

### Phase 23 — Wild Labs B: Economy, History, Mathematics
*12–16 days · Gate: novelty and archaeology queries return provenance*

1. **The Exchange Economy**: position-specific piece values derived from
   current activity/coordination; comparison against universal values; "what is
   this knight actually worth here".
2. **Chess Archaeology**: trace a position's structural ancestors through the
   corpus; timeline of appearances; earliest occurrence with provenance.
3. **Positional Fragility**: sensitivity of an advantage to small perturbations
   (tempo, one-piece moves, minor structural changes) using Phase 12 machinery.
4. **Move Consequence Explorer**: any legal move → full consequence report
   (diff, motifs, horizon, complexity) in one view; comparison strip of all
   moves.
5. **Theoretical Novelty Detector**: book + corpus coverage, transposition
   search, "unexplored territory" score with evidence and confidence caveats.
6. **Chess Mathematics Explorer**: zugzwang, opposition, triangulation,
   domination, parity, key squares — detected, explained, and verified.
7. UI: labs share the same workspace pattern; each has an explanation block
   generated from metadata.
8. Tests: fixtures per concept (e.g. known zugzwang studies, triangulation
   positions), determinism, provenance correctness, performance.

**Gate**: every lab passes its fixture; novelty/archaeology show provenance for
every claim.

---

### Phase 24 — Assistant Layer
*10–14 days · Gate: assistant disabled by default; grounded output only*

1. `assistant/adapter.py`: providers — disabled (default), local model (llama.cpp
   / ONNX LLM), or an OpenAI-compatible endpoint. Explicit configuration; keys
   never written to logs; a network indicator appears in the status bar while a
   request is in flight.
2. `assistant/grounding.py`: builds a **fact bundle** from the current
   `AnalysisResult` (findings, metrics, lines, model cards, trust labels). The
   assistant may only cite facts in the bundle. Numbers in the output are
   validated against the bundle and rejected if invented.
3. Prompt templates per task: explain this position, explain this move, compare
   two positions, summarise this autopsy, draft a report section. Templates are
   versioned and tested with golden outputs on a stub provider.
4. Explanation panel: ask/answer with citations; clicking a citation jumps the
   board to the evidence. Answers are labelled `NARRATIVE` and visually distinct
   from computed results.
5. Report drafting: generate `NARRATIVE` sections with citations; the author
   accepts, edits, or rejects; a diff view shows exactly what was added.
6. Privacy and control: local-first, redaction of file paths and personal data,
   per-request confirmation when a remote provider is configured, full
   conversation deletion.
7. Tests: grounding rejection, fabricated-number rejection, offline-disabled
   behaviour, prompt-injection resistance, provider timeout, cache determinism
   at temperature 0.

**Gate**: with the assistant disabled (default) nothing changes anywhere; with a
local model, every sentence cites a real finding; the fabrication tests fail
closed.

---

### Phase 25 — Hardening, Plugins, Packaging, v1.0
*14–20 days · Gate: v1.0 checklist*

1. **Performance pass 2**: whole-app profiling under a scripted session;
   array-backed TT; incremental eval for search; numba kernels only where
   measured; re-baseline every budget.
2. **Memory**: TT cap, bounded traces, streaming imports, 1M-position memory
   regression test.
3. **Chaos suite**: kill jobs at random points, hang/crash engines, corrupt
   DB/preset/assets, fill disk — every case has a documented recovery.
4. **Soak test**: 2-hour scripted session, 200 games, no RSS growth beyond cap,
   no leaked processes or files.
5. **Plugin API**: finalise `plugins/api.py`, manifest schema, permissions
   dialog, conformance suite, example plugin (a tiny custom analyzer) shipped
   in `examples/plugins/`.
6. **Packaging**: AppImage build + smoke test (launch, open PGN, analyze,
   export PDF); optional Flatpak manifest; desktop file, icons, MIME
   associations for `.pgn` and `.cob`. All 20 themes ship inside the bundle; no
   model weights do (explicit download only).
7. **Model and theme governance check**: every shipped model has a passing gate
   report; every theme passes validation; `ml.enabled=false` session still
   completes the full scripted run.
8. **Docs**: user guide per panel, "reading a report" guide, architecture doc,
   generated metrics/search references, model and theme guides, tutorial with
   gallery screenshots, diagnostics guide.
9. **Onboarding**: sample PGNs, demo workspace, 5-minute tour.
10. **Release**: changelog, `v1.0.0`, checksums, known-limitations document.

**Gate**: AppImage launches and completes the full scripted session on X11 and
Wayland; all budgets met; no P1/P2 issues; docs reviewed by someone who did not
write them.

---

## 16. Release Map

| Release | Contents | Phases | Cumulative (focused days) |
|---------|----------|--------|---------------------------|
| M0 | Green foundation + `./setup.sh` | 0 | 4–5 |
| M1 | Correct core | 1 | 14–19 |
| M2 | Own engine + federation | 2–3 | 34–47 |
| M3 | Explains (eval, DNA, geometry, graphs, CLI) | 4–5, 7–9 | 99–134 |
| **v0.1.0** | **Instrument**: designed workspace, 20 themes, board, eval/DNA/geometry/graph panels, PDF export | 6, 9 | 99–134 |
| **v0.2.0** | **Tactics + pawn labs** | 10–11 | 119–160 |
| **v0.3.0** | **What-if, exchange, horizon, complexity, criticality** | 12–13 | 143–192 |
| **v0.4.0** | **Scale + learning base**: corpus, ECO, book, ML infrastructure, similarity | 14–16 | 177–240 |
| **v0.5.0** | **Learning**: neural eval, policy guidance, MCTS, parity gates | 17 | 191–260 |
| **v0.6.0** | **Theory**: tablebases, fortresses, proofs | 18 | 211–286 |
| **v0.7.0** | **Narrative**: autopsy, genealogy, full reports | 19 | 225–304 |
| **v0.8.0** | **Observatory**: search inspection, workspace modes, notebook | 20 | 237–320 |
| **v0.9.0** | **Perception labs** (the six approved) | 21 | 249–338 |
| **v0.10.0** | **Dynamics + history/mathematics labs** | 22–23 | 271–368 |
| **v1.0.0** | **Complete**: assistant layer, hardening, plugins, packaging | 24–25 | 295–402 |

Honest reading: this is a **multi-year solo effort** (~295–405 focused days) —
about 1.5–2 years full-time, longer part-time. Every release from v0.1 is usable,
which is deliberate. The compressible parts are the perception labs (21), wild
labs (22–23), the assistant layer (24), and tablebase depth (18); everything else
is load-bearing for the rest.

---

## 17. Risk Register

| # | Risk | L | I | Mitigation |
|---|------|---|---|------------|
| R1 | Pure-Python search depth/strength | H | M | Kernel boundary; depth 8–12 is enough for an instrument; strength is not the product |
| R2 | Scope: 26 phases, no deferral | H | H | Usable releases from v0.1; gates enforced; effort re-estimated each milestone |
| R3 | "Numbers theatre" — metrics nobody trusts | M | H | Every metric: doc, unit, fixture, symmetry test, explanation sentence, golden review |
| R4 | Counterfactual semantics fuzziness | H | M | `LegalityReport` + explicit "undefined" language; never imply illegal states are legal |
| R5 | Multi-engine zoo (quirks, hangs, crashes) | H | M | Quirk flags + `FakeEngine` matrix; watchdogs; kill escalation; auto-restart |
| R6 | UI becomes the program | M | H | `services/` only; import-graph tests; CLI parity requirement |
| R7 | Visual ambition outruns maintainability | M | H | Design tokens + component library + screenshot goldens; no bespoke painting outside approved components |
| R8 | PDF layout engine complexity | M | M | Narrow scope (A4/Letter, sections, figures, tables); page-image goldens; no absolute positioning APIs |
| R9 | Tablebase time/disk | M | M | ≤ 4-man generation; resumable; disk preflight; 5-man probe-only |
| R10 | Golden fixtures ossify bugs | M | M | Reviewed updates + human plausibility pass at each milestone |
| R11 | Wayland/X11 divergence | M | L | Manual checklist per release; no global positioning; test fractional scaling |
| R12 | Cache staleness → wrong analyses | M | H | Version+params+model in key; explicit invalidation tests; stale badge in UI |
| R13 | Unlicensed assets (pieces/fonts/themes/data/weights) | M | H | `assets/LICENSES.md` ledger; CI check that every asset and model has an entry |
| R14 | Plugin API churn before v1.0 | M | M | API versioning from day one; conformance suite; only stabilize at v1.0 |
| R15 | GPL contamination from external engines | L | H | Never bundle; separate processes; license display; our code stays MIT |
| R16 | ML erodes trust ("is this real or guessed?") | M | H | Trust labels on every output; filters; ablation; classical default; model cards in reports |
| R17 | Silent model regressions | M | H | Model hash in every reproducibility record; no auto-update; gate reports required |
| R18 | GPU nondeterminism breaks reproducibility | H | M | CPU default; explicit determinism envelope per model; GPU marked `HW_DEPENDENT`; never in `Proof` mode |
| R19 | Training cost and hardware access | M | M | Small models first; CPU-first inference; GPU optional; gates before scale-up |
| R20 | Assistant hallucination | M | H | Grounding to a fact bundle; numeric validation; `NARRATIVE` label; disabled by default |
| R21 | 20-theme maintenance burden | M | M | Pack inheritance; automated token/contrast/colourblind tests; bounded golden matrix |
| R22 | ML dependency churn (torch, onnxruntime, providers) | M | M | Inference behind a protocol; torch train-only; versions pinned; classical fallback tested |
| R23 | Dataset/weight licensing surprises | M | M | Provenance manifests; openly licensed sources only; license shown at download |
| R24 | Perception-lab scope creep | M | M | Phase 21 has a fixed six-lab scope; anything else is a new decision and a new phase |

---

## 18. Open Questions (defaults are decided; change any of these)

### Product and platform

1. **Engine list**: Stockfish, Berserk, Ethereal, RubiChess, Igel preconfigured;
   Lc0 first-class as a neural reference; Maia optional for human-likeness.
2. **Tablebases**: generate ≤ 4-man ourselves; probe 5-man via Syzygy if the
   user supplies files.
3. **Fonts**: Inter + JetBrains Mono bundled (OFL).
4. **Piece sets**: two CC0/MIT sets bundled + user-supplied directory.
5. **Book play**: available but off by default in analysis.
6. **PDF page size**: A4 default, Letter selectable.
7. **Notebook storage**: inside the SQLite store; export to Markdown on demand.
8. **AppImage vs Flatpak**: AppImage primary; Flatpak optional.
9. **Labs order**: Dynamics (22) before History/Mathematics (23).

### AI/ML decisions (settled 2026-11-23)

Approved: 11–15, 18. Dropped: 16, 17, 19, 20. Q10 (neural default) remains
**opt-in through v1.0**. The defaults below are the locked behaviour.

10. **Neural evaluation default**: stays **opt-in** even if a model passes gates,
    or becomes the default evaluator? *Default: opt-in through v1.0.*
11. **Difficulty and human-likeness (Maia-style)**: **approved** — opt-in, clearly
    labelled, calibrated; coaching and puzzle calibration read from it.
12. **Board-image recognition**: **approved** — paste a diagram/screenshot,
    manual confirmation always required.
13. **Player style profiling**: **approved** — corpus-derived axes; every axis
    shows its evidence.
14. **Puzzle generation**: **approved** — uniqueness verified by search.
15. **Repertoire recommendation**: **approved** — explainable via features and
    statistics, not a black-box ranking.
16. **Learned opening book**: **dropped for v1.0** — the statistical book plus
    Polyglot is the whole book feature.
17. **Coach mode (interactive lessons)**: **dropped for v1.0** — the assistant
    explains positions; it does not run lessons.
18. **Blunder-risk prediction**: **approved** for the autopsy, with confidence
    intervals and explicit error rates.
19. **Engine-assistance detection**: **not planned** — high false-positive risk
    and social consequences.
20. **Personal model on your own games**: **not planned** — privacy and
    data-volume cost for little gain at typical game counts.
21. **Consensus weighting**: should neural engines (Lc0) count equally with
    classical engines in the consensus band, or be reported separately?
    *Default: reported in a separate `LEARNED` band.*

---

## 19. Immediate Next Actions (first commits)

1. `chore: safe.directory, .gitattributes, initial commit of planning docs`
2. `chore: scaffold uv project (src layout, pyproject, lock)`
3. `feat: setup.sh bootstrap — diagnose, install, verify, print launch command`
4. `chore: ruff/mypy/pytest/pre-commit configuration`
5. `chore: ubuntu CI with NUMBA_DISABLE_JIT, shellcheck, and import-graph guards`
6. `docs: ADR-0001..0005, 0017, 0018` (trust ladder, model governance, themes)
7. `feat(core): squares, bit helpers, attack tables`
8. `feat(core): pieces and packed moves`
9. `feat(core): Position snapshot + mailbox`
10. `feat(core): Zobrist keys`
11. `feat(core): pseudo-legal move generation`
12. `feat(core): legality filtering`
13. `feat(core): make/unmake with undo stack`
14. `test(core): perft suite + differential harness`
15. `feat(cli): chess-obs doctor skeleton`

---

## 20. Appendix — Checklists

### 20.1 New metric

- [ ] Registered with versioned id, unit, category, doc
- [ ] `docs/metrics.md` regenerated, diff reviewed
- [ ] Hand-computed fixture + symmetry test + edge cases (no pawns, 8 pawns,
      promotion-heavy, bare kings)
- [ ] Added to `dna_vN` if it belongs (version bump if dimensions changed)
- [ ] Explanation sentence in `explain.py`
- [ ] Visible in a panel **or** in a report section
- [ ] Benchmark if per-node or per-ply

### 20.2 New analyzer

- [ ] `Analyzer` with id, version, requires, params model
- [ ] Returns typed payload + layers + findings + metrics
- [ ] Registered; appears in CLI module list, UI panel registry, effort profiles
- [ ] Failure-isolation + cancellation + cache-key tests
- [ ] Renders in text/JSON/markdown
- [ ] Budget declared and benchmarked

### 20.3 New panel

- [ ] Built on `AnalysisPanel`; declares id/title/min size/default area
- [ ] Uses `services/` only; works with `modules=()` where possible
- [ ] Busy / empty / error / stale states
- [ ] Keyboard reachable, accessible names, tab order
- [ ] pytest-qt smoke + one interaction test
- [ ] Screenshot goldens (canonical themes, 1x + 2x) + representative shot for all 20
- [ ] Present in relevant presets without layout breakage

### 20.4 New engine integration

- [ ] `EngineSpec` entry with license, homepage, binary patterns, quirks
- [ ] Option map for threads/hash/multipv/syzygy
- [ ] `FakeEngine` quirks covered by tests
- [ ] Timeout/kill/restart verified
- [ ] License + source link shown in UI
- [ ] No binary committed

### 20.5 New model

- [ ] `ModelSpec` entry: id, version, sha256, size, architecture, license
- [ ] Model card in `docs/models/` with training data provenance and gate report
- [ ] `GateReport` passes the active parity profile (Elo, calibration, latency,
      ablation, CPU/GPU agreement)
- [ ] Determinism envelope declared; `Proof` mode compatibility stated
- [ ] Golden inference fixtures with documented tolerances
- [ ] Missing/corrupt artifact → visible warning + classical fallback
- [ ] Neural results labelled `LEARNED` in UI, reports, and exports
- [ ] No artifact committed to git; download is explicit and checksum-verified

### 20.6 New theme

- [ ] Pack TOML with metadata (name, id, variant, license, author, `based_on`)
- [ ] Token completeness + contrast + semantic-distinctness tests pass
- [ ] Colourblind simulation passes for accents and chart sequence
- [ ] Preview tile added to the theme browser
- [ ] Representative screenshots added to the golden matrix
- [ ] Print/PDF palette mapping verified
- [ ] Focus ring and disabled states legible in that theme

### 20.7 Release

- [ ] All phase gates for the milestone pass
- [ ] Budgets met; `baseline.json` updated
- [ ] Per-directory coverage gates met
- [ ] `metrics.md`, `search.md`, `models.md`, ADRs, changelog current
- [ ] Every theme validated; golden matrix updated for affected themes
- [ ] No unapproved perception lab in the tree; no model without a gate report
- [ ] AppImage built, smoke-tested on X11 and Wayland
- [ ] Scripted session: open → analyze → what-if → labs → export PDF
- [ ] Same session with `ml.enabled=false` (classical mode must be complete)
- [ ] `chess-obs doctor` clean
- [ ] No open P1/P2; known limitations documented
