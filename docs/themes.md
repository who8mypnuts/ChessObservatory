# Themes

> **Status:** the theme system and the 20 packs arrive in Phase 6. This page is
> the contract ([ADR-0018](adr/0018-theme-pack-system.md)).

A theme is **data**, not code: a TOML pack with metadata and token overrides.
Packs may inherit via `based_on`, so a new theme is often twenty lines.

## Shipped themes (20)

| Variant | Themes |
|---------|--------|
| Dark (12) | Observatory Dark (default), Midnight, Carbon, Slate, Nord, Gruvbox Dark, Solarized Dark, Tokyo Night, Catppuccin Mocha, Everforest, Kanagawa, Amber Terminal |
| Light (6) | Parchment, Observatory Light, Solarized Light, Catppuccin Latte, GitHub Light, Blueprint |
| Accessibility (2) | High Contrast Dark (7:1 targets), Deuteranopia Safe |

Board palettes are a separate token group, so any theme combines with any
palette: Classic Green, Walnut, Rosewood, Marble, Slate, Ice, Blueprint, Paper,
Monochrome, High Contrast.

## Pack shape

```toml
id = "midnight"
name = "Midnight"
variant = "dark"
license = "MIT"
author = "Chess Observatory"
based_on = "observatory-dark"

[colors]
accent = "#8B7CFF"
surface = "#121826"
```

Unknown tokens are errors. A pack cannot introduce a colour that widgets do not
understand, and Python code cannot hard-code hex values outside `tokens.py`.

## Validation (all 20, automated)

- Required tokens present (a missing key fails the build).
- Contrast: body text ≥ 4.5:1, large text and UI borders ≥ 3:1, accessibility
  themes ≥ 7:1.
- Semantic distinctness under simulated deuteranopia and tritanopia.
- Chart sequences and heat-map ramps have monotone lightness.

## Behaviour

- Instant switching, no restart; remembered per layout preset with its board
  palette and density.
- Theme browser with live preview tiles; import/export; user themes directory.
- Dark themes map to a print-safe light palette for HTML and PDF.
- Golden screenshots are bounded: four canonical themes across every panel, all
  twenty across three representative screens.
