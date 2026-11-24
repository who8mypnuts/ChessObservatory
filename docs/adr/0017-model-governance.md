# ADR-0017: Model governance and parity gates

## Status

Accepted, 2026-11-23.

## Context

A learned component can silently change every analysis in the product. Without
governance, "the evaluation changed" becomes unexplainable, cached results become
irreproducible, and a model update can regress the product unnoticed.

## Decision

Every model artifact is described by a `ModelSpec` in `ml/models/registry.py`:

- id, version, sha256, byte size, architecture, input fingerprint, licence,
  training dataset references, model-card path, determinism envelope, gate report.
- Artifacts are **optional downloads**, checksum-verified, never committed and
  never silently updated.
- A model is usable only if its `GateReport` passes the active profile: Elo versus
  the classical evaluator at fixed nodes, calibration (ECE), CPU latency p50/p99,
  ablation, CPU/GPU agreement, and the exact benchmark command.
- `reproducibility` records the model id and hash, so a replay can explain a
  difference rather than pretend there is none.
- Removing a dataset marks dependent models `orphaned` instead of leaving them
  quietly usable.
- Inference runs behind a protocol (ONNX Runtime); PyTorch is training-only.
- `ml.enabled=false` must leave the whole application working; that is an enforced
  test.

## Consequences

- Models are releases, with cards and numbers, not files copied into a directory.
- GPU results are marked `HW_DEPENDENT` and never used for `Proof` mode.
- The classical evaluator remains the reference until a gate passes.

## Alternatives considered

- *Auto-update to "latest"*: convenient, unreproducible, and impossible to audit.
- *Trust the loss curve*: loss does not predict playing strength or calibration.

*Slug: `model-governance`.*
