# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0.dev0] — 2026-11-23

Phase 0: foundations and guardrails. No chess logic yet; the point is that every
later phase inherits a green, tested, documented base.

### Added

- `uv` project (Python 3.14, `src/` layout, hatchling) with runtime, `[jit]`,
  `[ml]`, `[train]`, `[gpu]`, `[ann]` extras and a contributor dependency group.
- `chess-obs` CLI: `doctor`, `config show|path`, `ui`, `version`, plus
  `--config` and `--set` overrides.
- `setup.sh`: Linux/Python/uv/Qt detection, optional uv install, `uv sync`,
  verification, and the launch command. Modes: `--check`, `--with-*`, `--all`,
  `--run`, `-y`.
- Error taxonomy with stable codes and actionable hints.
- Layered configuration (defaults → TOML → environment → CLI) with provenance,
  validation and a tested v0→v1 migration.
- Canonical JSON serialization with strict typed dataclass decoding.
- Rotating file plus console logging, safe to configure twice.
- `chess-obs doctor`: guarded checks for OS, Python, package, PySide6, numpy,
  pyarrow, display, config/data/log/store directories, reference engines and the
  asset ledger; human and JSON output.
- Minimal Qt main window that opens offscreen and via `chess-obs ui`.
- Test layers: unit, property, differential (wired, awaiting Phase 1), UI,
  benchmark, plus architectural guards for imports, assets and docs.
- Continuous integration: lint, shellcheck, mypy strict, unit, property,
  differential, UI (offscreen), benchmark smoke, docs freshness, import graph,
  and a `NUMBA_DISABLE_JIT=1` leg.
- Documentation: architecture, position API, search, metrics, models, themes,
  user guide, gallery policy, and ADR-0001 … ADR-0020.

### Notes

- Import graph is enforced: Qt only in `ui/`; `python-chess` and `networkx` are
  test-only; future `numba`, `torch` and `onnxruntime` have fixed boundaries.
- All 20 theme packs and the designed workspace arrive in Phase 6.
