# ADR-0018: Theme packs as data (20 shipped themes)

## Status

Accepted, 2026-11-23.

## Context

The interface must look designed, not themed-by-accident, and users expect real
choice. Hand-coding each theme into widgets guarantees inconsistency and makes
accessibility checks impossible. Twenty themes must stay maintainable by one
person.

## Decision

- A theme is a **TOML pack** with metadata (`id`, `name`, `variant`, `license`,
  `author`, optional `based_on`) and token overrides. Packs may inherit, so a new
  theme is often twenty lines.
- 20 packs ship: 12 dark, 6 light, 2 accessibility (7:1 contrast, colourblind
  safe). Board palettes are a separate token group (10 palettes), so any theme
  combines with any board.
- `ui/design/tokens.py` is the only source of base values; packs override it.
- Automated validation for all packs: required-token completeness, WCAG contrast,
  semantic distinctness under simulated deuteranopia/tritanopia, and monotone
  heat-map ramps.
- Switching is instant, remembered per layout preset, and mapped to a print-safe
  palette for PDF/HTML.
- Golden screenshots are bounded: four canonical themes across every panel, all
  twenty across three representative screens, plus structural tests.

## Consequences

- Contributors can add a theme without touching Python.
- Accessibility is tested, not claimed.
- A theme can never introduce an unregistered colour into a widget.

## Alternatives considered

- *Qt palettes only*: cannot express charts, heat maps or board colours coherently.
- *One dark and one light theme*: simpler, but the product promise includes a
  workspace people enjoy spending hours in.

*Slug: `theme-pack-system`.*
