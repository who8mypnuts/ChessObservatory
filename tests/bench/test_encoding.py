"""Benchmark smoke: the harness works and the baseline is recorded."""

from __future__ import annotations

import pytest

from chess_observatory.config import Config, UiConfig
from chess_observatory.serialization import dumps

pytestmark = pytest.mark.bench


def test_config_json_encoding(benchmark) -> None:
    config = Config(ui=UiConfig(theme="midnight"))
    text = benchmark(lambda: dumps(config))
    assert '"theme":"midnight"' in text
