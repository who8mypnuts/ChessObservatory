# Models

> **Status:** the registry, inference and gates arrive in Phase 15. This page is
> the contract that phase implements ([ADR-0017](adr/0017-model-governance.md)).

Machine learning is **off by default**. With `models/` deleted and
`ml.enabled=false`, the application is complete and fully tested
([ADR-0005](adr/0005-ai-trust-ladder.md)).

## Trust

| Label | Meaning |
|-------|---------|
| `EXACT` | proven by enumeration or an independent verifier |
| `DERIVED` | a named deterministic algorithm |
| `LEARNED` | a versioned model plus a passing gate report |
| `NARRATIVE` | grounded generated prose |

A model may propose; it may not certify. Fortress candidates are proved, puzzle
uniqueness is verified by search, tablebase claims are exact.

## Registry entry

Every artifact is described by a `ModelSpec`:

```text
ModelSpec(id, version, sha256, bytes, architecture, input_fingerprint,
          license, trained_on=[DatasetRef...], card, determinism,
          gates=GateReport(...), trust=LEARNED)
```

Artifacts are optional downloads, checksum-verified, never committed, never
updated silently. `models/` is git-ignored; the database stores references only.

## Parity gates

A model is usable only when its gate report passes for the active profile:

| Gate | Question |
|------|----------|
| Elo at fixed nodes | Is it actually stronger than the classical evaluator? |
| Calibration (ECE) | Do its probabilities mean what they say? |
| Latency p50/p99 | Does it fit the runtime budget on the reference machine? |
| Ablation | Does removing it degrade gracefully, with no silent change? |
| CPU/GPU agreement | Do devices choose the same moves within tolerance? |

Every change ships `docs/experiments/NNNN-*.md` with the gate report and the
ablation. Model cards live in `docs/models/`.

## Repro notes

`reproducibility` records the model id and hash. GPU runs are marked
`HW_DEPENDENT` and are never used in `Proof` mode. Datasets carry sha256
manifests and stored splits, so a validation position cannot leak into training.
