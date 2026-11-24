"""Logging setup: one rotating file plus the console (plan §13.4).

The project logger is namespaced (``chess_observatory.*``) and never touches the
root logger, so a host application (or pytest) keeps its own logging intact.

Configuring twice is a no-op unless ``force=True``; this matters because the CLI
and tests both call it and duplicate handlers would double every line.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from chess_observatory.errors import ConfigError
from chess_observatory.paths import log_dir as default_log_dir

LOGGER_NAME = "chess_observatory"
HANDLER_MARK = "_chess_observatory_handler"
LOG_FILENAME = "chess-observatory.log"
MAX_BYTES = 2_000_000
BACKUP_COUNT = 3
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True, slots=True)
class LoggingSetup:
    """What :func:`configure_logging` actually produced."""

    level: str
    log_file: Path | None
    handlers: tuple[str, ...]


def get_logger(name: str) -> logging.Logger:
    """Return a logger inside the project namespace."""
    if name == LOGGER_NAME or name.startswith(LOGGER_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def _is_ours(handler: logging.Handler) -> bool:
    return bool(getattr(handler, HANDLER_MARK, False))


def _mark(handler: logging.Handler) -> logging.Handler:
    setattr(handler, HANDLER_MARK, True)
    return handler


def configure_logging(
    level: str = "INFO",
    *,
    log_directory: Path | None = None,
    console: bool = True,
    force: bool = False,
) -> LoggingSetup:
    """Configure file and console logging for the project namespace."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False

    ours = [handler for handler in logger.handlers if _is_ours(handler)]
    if ours and not force:
        return _describe(logger)

    for handler in ours:
        logger.removeHandler(handler)
        handler.close()

    resolved = logging.getLevelName(str(level).upper())
    if not isinstance(resolved, int):
        raise ConfigError(
            f"Unknown log level {level!r}.",
            hint="Use DEBUG, INFO, WARNING, ERROR or CRITICAL.",
            context={"level": level},
        )
    logger.setLevel(resolved)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    directory = Path(log_directory) if log_directory is not None else default_log_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            directory / LOG_FILENAME,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        # A working CLI beats a hard failure over an unwritable log directory.
        pass
    else:
        file_handler.setFormatter(formatter)
        logger.addHandler(_mark(file_handler))

    if console:
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setFormatter(formatter)
        logger.addHandler(_mark(stream_handler))

    return _describe(logger)


def _describe(logger: logging.Logger) -> LoggingSetup:
    handlers = tuple(type(handler).__name__ for handler in logger.handlers if _is_ours(handler))
    log_file: Path | None = None
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and _is_ours(handler):
            log_file = Path(handler.baseFilename)
            break
    return LoggingSetup(
        level=logging.getLevelName(logger.level),
        log_file=log_file,
        handlers=handlers,
    )
