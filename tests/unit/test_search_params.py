"""Parameter registry: defaults, validation, round-trip and generated docs."""

from __future__ import annotations

import pytest

from chess_observatory.search.params import (
    DEFAULT_PARAMS,
    Determinism,
    Param,
    ParamRegistry,
    ParamTier,
    ParamType,
)

EXPECTED_DEFAULTS = {
    "search.max_depth": (32.0, 1.0, 100.0),
    "search.multipv": (1.0, 1.0, 32.0),
    "search.hash_mb": (256.0, 16.0, 1024.0),
    "search.threads": (1.0, 1.0, 16.0),
    "search.delta_prune": (1.0, None, None),
}


def test_registry_declares_the_phase_2_knobs() -> None:
    registry = ParamRegistry()
    assert set(DEFAULT_PARAMS) == set(EXPECTED_DEFAULTS)
    assert "search.max_depth" in registry
    assert len(registry) == 5
    for name in EXPECTED_DEFAULTS:
        assert registry.get(name) is not None, name


def test_defaults_and_ranges_are_reported() -> None:
    registry = ParamRegistry()
    max_depth = registry["search.max_depth"]
    assert max_depth.default == 32.0
    assert max_depth.min == 1.0
    assert max_depth.max == 100.0
    assert max_depth.step == 1.0
    assert max_depth.tier is ParamTier.INTERMEDIATE
    assert max_depth.determinism is Determinism.ALWAYS
    assert max_depth.restart_required is False
    delta = registry["search.delta_prune"]
    assert delta.type is ParamType.BOOL
    assert delta.determinism is Determinism.ALWAYS
    assert delta.restart_required is False


def test_threads_are_hardware_dependent_and_restart_required() -> None:
    registry = ParamRegistry()
    threads = registry["search.threads"]
    assert threads.determinism is Determinism.HARDWARE_DEPENDENT
    assert threads.restart_required is True


def test_validate_accepts_values_inside_the_range() -> None:
    registry = ParamRegistry()
    assert registry.validate("search.max_depth", 64) == 64.0
    assert registry.validate("search.threads", 4) == 4.0


def test_validate_accepts_boundaries() -> None:
    registry = ParamRegistry()
    assert registry.validate("search.max_depth", 1) == 1.0
    assert registry.validate("search.max_depth", 100) == 100.0


def test_validate_rejects_values_outside_the_range() -> None:
    registry = ParamRegistry()
    with pytest.raises(ValueError, match="below the minimum"):
        registry.validate("search.max_depth", 0)
    with pytest.raises(ValueError, match="above the maximum"):
        registry.validate("search.max_depth", 101)
    with pytest.raises(KeyError):
        registry["search.does_not_exist"]


def test_clamp_pushes_values_into_range() -> None:
    param = Param("search.max_depth", default=32.0, min=1.0, max=100.0)
    assert param.clamp(500.0) == 100.0
    assert param.clamp(-3.0) == 1.0
    assert param.validate(7.0) == 7.0


def test_to_dict_and_from_dict_round_trip() -> None:
    registry = ParamRegistry()
    again = ParamRegistry.from_dict(registry.to_dict())
    assert again.to_dict() == registry.to_dict()
    assert again["search.max_depth"].default == registry["search.max_depth"].default
    assert again["search.delta_prune"].default == registry["search.delta_prune"].default


def test_render_markdown_lists_every_registered_parameter() -> None:
    registry = ParamRegistry()
    markdown = registry.render_markdown()
    for name, (default, _min, _max) in EXPECTED_DEFAULTS.items():
        param = registry[name]
        assert name in markdown
        assert f"`{name}`" in markdown
        assert str(int(default)) in markdown
        assert param.doc in markdown
    assert "## Parameters" in markdown
    assert "## Reproducibility" in markdown
    assert "first-class, inspectable subsystem" in markdown
    assert "true" in markdown and "hardware_dependent" in markdown


def test_registry_is_frozen_style_immutable_by_convention() -> None:
    registry = ParamRegistry()
    assert list(iter(registry)) == sorted(DEFAULT_PARAMS)
    assert len(registry) == len(DEFAULT_PARAMS)
