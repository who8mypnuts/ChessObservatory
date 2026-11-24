# Asset licence ledger

Every file under `assets/` must appear in the table below with its licence,
source and required attribution (plan §13.1, R13). CI fails on an unlisted
asset, and fails on an entry whose file does not exist.

Rules:

- One row per asset file, with the path relative to `assets/`.
- `License` must be an SPDX identifier or an unambiguous name (e.g. `CC0-1.0`,
  `MIT`, `OFL-1.1`).
- `Source` is the upstream project or URL the file came from.
- `Attribution` is the exact credit text the licence requires, or `—` if none.
- Never commit an asset whose licence forbids redistribution.

## Bundled assets

| Path | Kind | License | Source | Attribution |
|------|------|---------|--------|-------------|

## Planned categories

Nothing is bundled yet. These categories are populated in later phases, and each
file will be added to the table above when it lands:

- `pieces/` — two vetted CC0/MIT piece sets (Phase 6)
- `icons/`, `fonts/` — interface assets (Phase 6)
- `themes/` — the 20 theme packs, with upstream palette credits (Phase 6)
- `board_palettes/` — board colour definitions (Phase 6)
- `samples/` — the sample PGN corpus (Phase 14)
- `models/examples/` — tiny fixtures, never trained weights (Phase 15)
