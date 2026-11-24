"""Property: any valid configuration survives a file round-trip."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from chess_observatory.config import Config, SearchConfig, UiConfig, load_config, save_config

TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    max_size=40,
)


@pytest.mark.property
@settings(max_examples=50, deadline=None)
@given(
    theme=TEXT,
    board_palette=TEXT,
    motion=st.booleans(),
    threads=st.integers(min_value=1, max_value=4096),
    hash_mb=st.integers(min_value=1, max_value=65536),
)
def test_config_file_round_trip(
    theme: str,
    board_palette: str,
    motion: bool,
    threads: int,
    hash_mb: int,
) -> None:
    original = Config(
        ui=UiConfig(theme=theme, board_palette=board_palette, motion=motion),
        search=SearchConfig(threads=threads, hash_mb=hash_mb),
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.toml"
        save_config(original, path)
        assert load_config(path, env={}).config == original
