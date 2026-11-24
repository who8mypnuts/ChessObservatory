# Gallery

Approved reference screenshots live here once the designed workspace lands in
Phase 6.

## Policy

- Images are generated offscreen (`QT_QPA_PLATFORM=offscreen`) with fixed fonts,
  DPI and window size.
- The golden matrix is bounded on purpose:
  - four canonical themes (Observatory Dark, Parchment, High Contrast Dark,
    Carbon) across every panel and both full-screen modes;
  - all twenty themes across three representative screens: board + evaluation,
    graph analysis, and a PDF page.
- A visual change updates the affected images in the same commit and the diff is
  reviewed like code.
- Structural tests (token completeness, contrast, palette math) cover every
  theme; pixel tests never do.

Until then this directory intentionally contains no images.
