# Fuzz layer placeholder.

Randomised robustness tests arrive with the parsers they exercise: FEN and PGN
in Phase 1, UCI in Phase 3, configuration and store migrations in Phase 14. The
directory exists now so the layer is part of the layout, the marker is declared
in `pyproject.toml`, and CI can add the job without restructuring.
