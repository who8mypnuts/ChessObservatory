# ADR-0003: Kernel boundary: pure Python reference, numpy batches, optional numba

## Status

Accepted, 2026-11-23.

## Context

Python is the right language for a research workstation, but chess inner loops
are allocation- and branch-heavy. Rewriting the core in C++ at the start would
trade iteration speed for performance we cannot yet measure. Rewriting it in
numba immediately would make every debugger and profiler worse.

## Decision

Define one kernel API with three backends behind it:

1. **Pure Python** is the reference and the default. It is always correct, always
   debuggable, and always available.
2. **numpy** handles batch-shaped work (corpus scans, encodings, heat-map
   accumulation, similarity).
3. **numba** is an optional extra (`[jit]`) for proven hot spots only.

Rules that keep this honest:

- An algorithm is defined exactly once; backends implement it, they do not fork it.
- Every backended function has an equivalence test against the pure version.
- CI runs the full suite with `NUMBA_DISABLE_JIT=1`.
- A function earns a numba backend only with a recorded benchmark and a measured
  regression budget.

## Consequences

- Early phases are slower than a C++ core, which is acceptable: depth 8–12 is
  plenty for an instrument, and correctness comes first.
- The optimisation path is incremental and reversible.
- Optional dependencies never become hidden requirements.

## Alternatives considered

- *C++/Rust core from day one*: better peak performance, much slower iteration,
  harder contribution, and no measurable need before Phase 2.
- *numba everywhere*: compile times and opaque tracebacks for code that runs once.

*Slug: `kernel-boundary`.*
