"""Differential oracle suite.

The real differential tests start in Phase 1, once the rules core exists and can
be compared move-for-move against ``python-chess``. The marker and CI job exist
now so the layer is wired from day one rather than bolted on later.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.differential


@pytest.mark.skip(reason="Rules core and python-chess oracle arrive in Phase 1.")
def test_movegen_matches_python_chess() -> None:
    """Placeholder: perft and random-game differential comparison."""
