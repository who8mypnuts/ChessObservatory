"""Canonical JSON and strict typed decoding."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

import pytest

from chess_observatory.errors import ChessObservatoryError, SerializationError
from chess_observatory.serialization import dumps, from_dataclass, loads, to_jsonable


class Colour(StrEnum):
    RED = "red"
    BLUE = "blue"


@dataclass(frozen=True, slots=True)
class Inner:
    value: int
    label: str = "inner"


@dataclass(frozen=True, slots=True)
class Outer:
    name: str
    colour: Colour
    inner: Inner
    tags: list[str]
    scores: dict[str, float]
    path: Path
    note: str | None = None
    mode: Literal["fast", "deep"] = "fast"
    extras: list[int] = field(default_factory=list)


def sample() -> Outer:
    return Outer(
        name="position",
        colour=Colour.BLUE,
        inner=Inner(7),
        tags=["a", "b"],
        scores={"white": 0.4},
        path=Path("data/store.sqlite"),
        mode="deep",
    )


def test_dumps_is_canonical_and_sorted() -> None:
    assert dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert dumps({"text": "café"}) == '{"text":"café"}'
    assert dumps({}, indent=2) == "{}"


def test_to_jsonable_handles_datetime_path_enum_and_sets() -> None:
    moment = dt.datetime(2026, 11, 23, 12, 0, tzinfo=dt.UTC)
    payload = to_jsonable(
        {
            "when": moment,
            "path": Path("/tmp/x"),
            "colour": Colour.RED,
            "items": {3, 1, 2},
        }
    )
    assert payload["when"] == "2026-11-23T12:00:00+00:00"
    assert payload["path"] == "/tmp/x"
    assert payload["colour"] == "red"
    assert payload["items"] == [1, 2, 3]


def test_unsupported_type_is_named() -> None:
    with pytest.raises(SerializationError) as caught:
        to_jsonable(object())
    assert "object" in str(caught.value)


def test_invalid_json_is_reported_with_position() -> None:
    with pytest.raises(SerializationError) as caught:
        loads("{not json}")
    assert "line 1" in str(caught.value)


def test_round_trip_through_json_text() -> None:
    original = sample()
    restored = from_dataclass(Outer, json.loads(dumps(original)))
    assert restored == original
    assert isinstance(restored.colour, Colour)
    assert isinstance(restored.path, Path)


def test_unknown_field_is_rejected() -> None:
    data = json.loads(dumps(sample()))
    data["surprise"] = 1
    with pytest.raises(SerializationError) as caught:
        from_dataclass(Outer, data)
    assert "surprise" in str(caught.value)


def test_missing_required_field_is_rejected() -> None:
    data = json.loads(dumps(sample()))
    del data["name"]
    with pytest.raises(SerializationError) as caught:
        from_dataclass(Outer, data)
    assert "Outer.name" in str(caught.value)


def test_nested_error_names_the_full_path() -> None:
    data = json.loads(dumps(sample()))
    data["inner"]["value"] = "seven"
    with pytest.raises(SerializationError) as caught:
        from_dataclass(Outer, data)
    assert "Outer.inner.value" in str(caught.value)


def test_bool_is_not_accepted_as_int_and_float_is_not_accepted_as_int() -> None:
    data = json.loads(dumps(sample()))
    data["inner"]["value"] = True
    with pytest.raises(SerializationError):
        from_dataclass(Outer, data)
    data["inner"]["value"] = 2.5
    with pytest.raises(SerializationError):
        from_dataclass(Outer, data)


def test_invalid_enum_value_is_named() -> None:
    data = json.loads(dumps(sample()))
    data["colour"] = "green"
    with pytest.raises(SerializationError) as caught:
        from_dataclass(Outer, data)
    assert "Colour" in str(caught.value)


def test_optional_field_accepts_null_and_rejects_wrong_type() -> None:
    data = json.loads(dumps(sample()))
    data["note"] = None
    assert from_dataclass(Outer, data).note is None
    data["note"] = 12
    with pytest.raises(SerializationError) as caught:
        from_dataclass(Outer, data)
    assert "Outer.note" in str(caught.value)


def test_literal_field_is_validated() -> None:
    data = json.loads(dumps(sample()))
    data["mode"] = "quick"
    with pytest.raises(SerializationError):
        from_dataclass(Outer, data)


def test_defaults_and_default_factories_fill_missing_fields() -> None:
    data = json.loads(dumps(sample()))
    del data["extras"]
    del data["inner"]["label"]
    restored = from_dataclass(Outer, data)
    assert restored.extras == []
    assert restored.inner.label == "inner"


def test_serialization_error_is_a_project_error() -> None:
    assert issubclass(SerializationError, ChessObservatoryError)
