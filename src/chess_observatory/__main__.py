"""Allow ``python -m chess_observatory``."""

from __future__ import annotations

from chess_observatory.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
