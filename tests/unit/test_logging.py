"""Logging: one file handler, one console handler, idempotent setup."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from chess_observatory.errors import ConfigError
from chess_observatory.logging import (
    HANDLER_MARK,
    LOGGER_NAME,
    configure_logging,
    get_logger,
)


@pytest.fixture(autouse=True)
def clean_project_logger() -> Iterator[None]:
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        if getattr(handler, HANDLER_MARK, False):
            logger.removeHandler(handler)
            handler.close()


def test_configures_file_and_console_handlers(tmp_path: Path) -> None:
    setup = configure_logging("DEBUG", log_directory=tmp_path, force=True)
    assert setup.level == "DEBUG"
    assert setup.handlers == ("RotatingFileHandler", "StreamHandler")
    assert setup.log_file == tmp_path / "chess-observatory.log"

    get_logger("tests").debug("hello file")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    assert "hello file" in setup.log_file.read_text(encoding="utf-8")


def test_second_call_is_a_no_op_until_forced(tmp_path: Path) -> None:
    first = configure_logging("INFO", log_directory=tmp_path, force=True)
    second = configure_logging("ERROR", log_directory=tmp_path / "other")
    assert second == first

    forced = configure_logging("ERROR", log_directory=tmp_path / "other", force=True)
    assert forced.level == "ERROR"
    assert forced.log_file == tmp_path / "other" / "chess-observatory.log"


def test_invalid_level_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        configure_logging("LOUD", log_directory=tmp_path, force=True)
    assert "LOUD" in str(caught.value)


def test_unwritable_log_directory_degrades_to_console(tmp_path: Path) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("file", encoding="utf-8")
    setup = configure_logging("INFO", log_directory=blocker, force=True)
    assert setup.log_file is None
    assert setup.handlers == ("StreamHandler",)


def test_get_logger_stays_in_the_project_namespace() -> None:
    assert get_logger("ui").name == "chess_observatory.ui"
    assert get_logger("chess_observatory.cli").name == "chess_observatory.cli"
    assert get_logger(LOGGER_NAME).name == LOGGER_NAME


def test_console_can_be_disabled(tmp_path: Path) -> None:
    setup = configure_logging("INFO", log_directory=tmp_path, console=False, force=True)
    assert setup.handlers == ("RotatingFileHandler",)
