# ADR-0002: Hybrid engine: own analytical core plus UCI federation

## Status

Accepted, 2026-11-23.

## Context

The instrument needs two things that pull in opposite directions: deep,
inspectable analysis of *our own* evaluation, and credible cross-checks against
strong engines. Building a world-class engine is a different multi-year project;
depending entirely on external engines makes the analysis a black box.

## Decision

Ship both, with clear roles:

- The **own engine** is the analytical core: decomposed evaluation, search traces,
  counterfactuals, learned-guidance experiments. Its knobs are first-class and
  generated from one parameter registry.
- **External engines** speak UCI through supervised subprocesses. Stockfish,
  Berserk, Ethereal, RubiChess and Igel are preconfigured; Lc0 is a first-class
  neural reference and Maia is optional for human-likeness work.
- Binaries are **never bundled**. The registry records licence, version, kind and
  (for neural engines) weight licensing. Installation is user-initiated and
  checksum-verified.
- Consensus is a **band**, not a vote: disagreement is shown with both lines and
  our evaluator's verdict, and neural engines are labelled `LEARNED` rather than
  treated as ground truth.

## Consequences

- Process supervision is real engineering: timeouts, crash isolation, quirk
  flags and a `FakeEngine` test matrix (Phase 3).
- Licence hygiene is enforced at the registry boundary; our code stays MIT.
- Users get strength where they want it without losing explainability.

## Alternatives considered

- *Own engine only*: honest, but weaker cross-checks and no ecosystem.
- *External engines only*: cheap, but turns the product into a front end and
  removes the decomposed-evaluation premise.

*Slug: `hybrid-engine-federation`.*
