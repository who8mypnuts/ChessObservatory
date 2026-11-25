# Chess Observatory

Go ahead, be a chess nerd.

A computational chess research workstation: an instrument for *why* a position
works, not just who is winning. It pairs an inspectable analytical engine with a
first-class federation of external UCI engines, and it never confuses a measured
fact with a guess.

> **Status: Phase 1 — rules core.** The application shell, CLI, configuration,
> diagnostics and test/CI scaffolding are real and tested, and the bitboard rules
> core now plays, edits, reads and writes chess. Search arrives in Phase 2; the
> designed workspace and 20 themes in Phase 6. See the
> [implementation plan](planning_docs/implementation_plan.md).

## Quick start

```bash
./setup.sh            # diagnose, install, verify, and print the launch command
./setup.sh --check    # diagnose only; change nothing
./setup.sh --run      # set up, then open the workspace
```

The bootstrap targets Linux (X11 and Wayland), Python 3.14+, and
[uv](https://docs.astral.sh/uv/). It never uses `sudo`; missing system libraries
are reported with the exact package-manager command. Optional extras:
`--with-ml`, `--with-train`, `--with-gpu`, `--with-ann`, or `--all`.

When it finishes, start the workspace with:

```bash
uv run chess-obs ui
```

Everything works with machine learning disabled. That is the default.

## What works today

```bash
uv run chess-obs doctor          # 13 guarded environment checks, human output
uv run chess-obs doctor --json   # machine-readable report for bug reports
uv run chess-obs config show     # effective configuration and its source
uv run chess-obs config path     # where the user config file lives
uv run chess-obs version         # version and install location
uv run chess-obs ui              # the Phase 0 window (Qt)
```

Configuration is layered: defaults → user TOML → environment → CLI, with
per-value provenance. See the [user guide](docs/user/README.md).

## Development

```bash
uv sync                       # install runtime + contributor dependencies
uv run pre-commit install     # optional: fast checks on commit
uv run ruff check .           # lint
uv run ruff format --check .  # formatting
uv run mypy                   # strict typing over src/
uv run pytest                 # every test layer
```

Test layers mirror CI:

```bash
uv run pytest tests/unit -q
uv run pytest tests/property -q
uv run pytest tests/differential -q
uv run pytest tests/ui -q            # needs QT_QPA_PLATFORM=offscreen headless
uv run pytest tests/bench -q
python3 tools/check_docs.py          # links, ADR index, required docs
```

The rules core has its own gates: a differential run against `python-chess` and
a recorded performance baseline.

```bash
uv run python tools/differential.py --games 2000    # CI gate
uv run python tools/differential.py --games 100000  # local gate, takes a while
uv run python tools/bench_core.py                   # measure
uv run python tools/bench_core.py --check           # compare with baseline.json
```

The Qt UI can be smoke-tested without a display:

```bash
QT_QPA_PLATFORM=offscreen uv run chess-obs ui --smoke
```

Architectural rules are enforced by tests, not convention: Qt only in `ui/`,
`python-chess` and `networkx` only in tests, and fixed boundaries for `numba`,
`torch` and `onnxruntime`. See [Architecture](docs/architecture.md).

## Project layout

```text
src/chess_observatory/   package: rules core, CLI, config, health, serialization, UI shell
tests/                   unit, property, differential, UI, benchmark, fuzz, chaos
docs/                    architecture, contracts, user guide, gallery, 20 ADRs
assets/                  licensing ledger (every bundled asset is listed)
planning_docs/           the authoritative implementation plan
tools/                   docs check, differential harness, performance baseline
setup.sh                 Linux bootstrap: diagnose, install, verify, launch
```

## Documentation

- [Architecture](docs/architecture.md) — layering and enforced dependency rules.
- [Position API](docs/position-api.md) — the rules-core contract (Phase 1).
- [Search](docs/search.md) — engine parameters and determinism (Phase 2).
- [Metrics](docs/metrics.md) — the feature registry contract (Phase 4).
- [Models](docs/models.md) — model cards, gates and trust labels (Phase 15).
- [Themes](docs/themes.md) — 20 theme packs and board palettes (Phase 6).
- [ADRs](docs/adr/README.md) — decisions that shape the codebase.
- [Changelog](CHANGELOG.md).

## Requirements

- Linux (X11 or Wayland). Windows and macOS are out of scope for v1.0.
- Python 3.14+ and [uv](https://docs.astral.sh/uv/).
- Qt runtime libraries; `./setup.sh` names the exact packages for your distro.

## Licence

MIT. See [LICENSE](LICENSE); bundled assets and any model weights are tracked in
[assets/LICENSES.md](assets/LICENSES.md).
