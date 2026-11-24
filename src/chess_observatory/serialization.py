"""Canonical JSON and typed dataclass decoding (plan §6.8).

One serializer decides JSON shape, so cached analyses, CLI output, reports and
plugins never disagree. Encoding is deterministic: sorted keys, no ASCII
escaping, compact separators.

Decoding is deliberately strict: unknown fields are errors, not ignored, and a
mismatched type raises :class:`SerializationError` naming the path.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import json
from collections.abc import Mapping
from dataclasses import MISSING, fields
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from chess_observatory.errors import SerializationError


def to_jsonable(value: object) -> object:
    """Convert a value tree to JSON-compatible primitives."""
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, enum.Enum):
        return to_jsonable(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [to_jsonable(item) for item in value]
    raise SerializationError(
        f"Cannot serialise value of type {type(value).__name__}.",
        hint="Add an explicit conversion in chess_observatory.serialization.",
        context={"type": type(value).__name__},
    )


def dumps(value: object, *, indent: int | None = None) -> str:
    """Canonical JSON text for any supported value tree."""
    separators = (",", ":") if indent is None else (",", ": ")
    return json.dumps(
        to_jsonable(value),
        sort_keys=True,
        ensure_ascii=False,
        indent=indent,
        separators=separators,
    )


def loads(text: str) -> object:
    """Parse JSON text, converting syntax errors to :class:`SerializationError`."""
    try:
        parsed: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SerializationError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}.",
            context={"line": exc.lineno, "column": exc.colno},
        ) from exc
    return parsed


def from_dataclass[T](cls: type[T], data: Mapping[str, object]) -> T:
    """Build ``cls`` from decoded JSON, validating every field."""
    result: T = _from_dataclass(cls, data, cls.__name__)
    return result


def _from_dataclass(cls: type[Any], data: Mapping[str, object], root: str) -> Any:
    if not dataclasses.is_dataclass(cls):
        raise SerializationError(f"{cls.__name__} is not a dataclass.")
    hints = get_type_hints(cls)
    declared = {field.name: field for field in fields(cls)}
    unknown = sorted(set(data) - set(declared))
    if unknown:
        raise SerializationError(
            f"{root}: unknown field(s): {', '.join(unknown)}.",
            context={"class": cls.__name__, "fields": unknown},
        )

    kwargs: dict[str, Any] = {}
    for name, field in declared.items():
        path = f"{root}.{name}"
        if name in data:
            kwargs[name] = _convert(hints[name], data[name], path)
        elif field.default is MISSING and field.default_factory is MISSING:
            raise SerializationError(
                f"{path} is required but missing.",
                context={"class": cls.__name__, "field": name},
            )
    return cls(**kwargs)


def _convert(annotation: Any, value: object, path: str) -> Any:
    if annotation is Any or annotation is object:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is UnionType or origin is Union:
        return _convert_union(args, value, path)

    if origin is Literal:
        if value not in args:
            raise SerializationError(
                f"{path}: expected one of {list(args)!r}, got {value!r}.",
                context={"path": path},
            )
        return value

    if origin in (list, tuple, set, frozenset) or annotation in (list, tuple, set, frozenset):
        if not isinstance(value, list | tuple):
            raise SerializationError(f"{path}: expected an array, got {type(value).__name__}.")
        item_type = args[0] if args else Any
        items = [_convert(item_type, item, f"{path}[{index}]") for index, item in enumerate(value)]
        container = origin or annotation
        if container in (set, frozenset):
            return container(items)
        if container is tuple:
            return tuple(items)
        return items

    if origin in (dict, Mapping) or annotation in (dict, Mapping):
        if not isinstance(value, Mapping):
            raise SerializationError(f"{path}: expected an object, got {type(value).__name__}.")
        key_type, value_type = args if len(args) == 2 else (str, Any)
        if key_type is not str:
            raise SerializationError(f"{path}: only string keys are supported.")
        return {
            str(key): _convert(value_type, item, f"{path}.{key}") for key, item in value.items()
        }

    if annotation is type(None):
        if value is not None:
            raise SerializationError(f"{path}: expected null, got {type(value).__name__}.")
        return None

    if isinstance(annotation, type):
        if dataclasses.is_dataclass(annotation):
            if not isinstance(value, Mapping):
                raise SerializationError(
                    f"{path}: expected an object for {annotation.__name__}, "
                    f"got {type(value).__name__}."
                )
            return _from_dataclass(annotation, value, path)
        if issubclass(annotation, enum.Enum):
            try:
                return annotation(value)
            except (ValueError, KeyError) as exc:
                raise SerializationError(
                    f"{path}: {value!r} is not a valid {annotation.__name__}.",
                    context={"path": path},
                ) from exc
        if annotation is Path:
            if not isinstance(value, str):
                raise SerializationError(f"{path}: expected a path string.")
            return Path(value)
        if annotation is bool:
            if not isinstance(value, bool):
                raise SerializationError(f"{path}: expected a boolean, got {type(value).__name__}.")
            return value
        if annotation in (int, float):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise SerializationError(f"{path}: expected a number, got {type(value).__name__}.")
            if annotation is int and not isinstance(value, int):
                raise SerializationError(f"{path}: expected an integer, got a float.")
            return value
        if annotation is str:
            if not isinstance(value, str):
                raise SerializationError(f"{path}: expected a string, got {type(value).__name__}.")
            return value

    raise SerializationError(
        f"{path}: unsupported annotation {annotation!r}.",
        hint="Teach chess_observatory.serialization._convert about this type.",
        context={"path": path},
    )


def _convert_union(args: tuple[Any, ...], value: object, path: str) -> Any:
    if value is None and type(None) in args:
        return None
    failures: list[str] = []
    for candidate in args:
        if candidate is type(None):
            continue
        try:
            return _convert(candidate, value, path)
        except SerializationError as exc:
            failures.append(str(exc))
    expected = " | ".join(getattr(arg, "__name__", str(arg)) for arg in args)
    raise SerializationError(
        f"{path}: value {value!r} does not match {expected}.",
        hint="; ".join(failures),
        context={"path": path},
    )
