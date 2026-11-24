# ADR-0014: Threading and process model

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Analysis runs off the GUI thread through a job system with cancellation; external engines are subprocesses with watchdogs; numpy and ONNX release the GIL where it matters. The GUI thread never blocks for more than 50 ms.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `threading`.*
