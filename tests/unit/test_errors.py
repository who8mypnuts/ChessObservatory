"""Error taxonomy contract."""

from __future__ import annotations

import pytest

from chess_observatory import errors
from chess_observatory.errors import (
    ChessObservatoryError,
    ConfigParseError,
    IllegalMoveError,
    InvalidFenError,
)


def _all_error_classes() -> list[type[ChessObservatoryError]]:
    seen: list[type[ChessObservatoryError]] = []
    queue = [ChessObservatoryError]
    while queue:
        cls = queue.pop(0)
        seen.append(cls)
        queue.extend(cls.__subclasses__())
    return seen


def test_str_contains_message_and_default_hint() -> None:
    error = InvalidFenError("bad placement field")
    text = str(error)
    assert "bad placement field" in text
    assert "six FEN fields" in text


def test_explicit_hint_overrides_default_and_can_be_empty() -> None:
    error = IllegalMoveError("Nf6 is not legal", hint="")
    assert error.hint == ""
    assert str(error) == "Nf6 is not legal"


def test_context_is_copied_and_serialised() -> None:
    source = {"fen": "8/8/8/8/8/8/8/K6k w - - 0 1"}
    error = InvalidFenError("bad fen", context=source)
    source["fen"] = "mutated"
    assert error.context["fen"].startswith("8/8")
    payload = error.to_dict()
    assert payload["code"] == "core.invalid_fen"
    assert payload["message"] == "bad fen"
    assert payload["hint"] == InvalidFenError.default_hint


def test_every_error_has_a_unique_dotted_code() -> None:
    classes = _all_error_classes()
    codes = [cls.code for cls in classes]
    assert len(codes) == len(set(codes)), f"duplicate codes: {codes}"
    for cls in classes:
        assert cls.code, cls
        assert "." in cls.code, cls
        assert cls.code == cls.code.lower(), cls


def test_every_error_is_catchable_as_the_base() -> None:
    with pytest.raises(ChessObservatoryError):
        raise IllegalMoveError("bad move")


def test_core_codes_share_their_parent_namespace() -> None:
    for cls in errors.CoreError.__subclasses__():
        assert cls.code.startswith("core.")


def test_config_parse_error_is_a_config_error() -> None:
    error = ConfigParseError("nope")
    assert isinstance(error, errors.ConfigError)
    assert error.code == "config.parse"
