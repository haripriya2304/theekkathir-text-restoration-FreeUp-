"""
utils.py
========

Shared, low-level helpers used across the Tamil Text Restoration Engine:
logging setup and Tamil/English token classification primitives.

Keeping these in one place avoids duplicating regex patterns across
modules and gives every module a consistently configured logger.
"""

from __future__ import annotations

import logging
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from text_cleaner import config


_TAMIL_BLOCK_PATTERN = re.compile(r"[\u0B80-\u0BFF]")


_PURE_TAMIL_TOKEN_PATTERN = re.compile(r"^[\u0B80-\u0BFF]+$")


_ASCII_ALPHA_TOKEN_PATTERN = re.compile(r"^[A-Za-z]+$")


def contains_tamil(text: str) -> bool:
    """Return True if *text* contains at least one Tamil character."""
    return bool(_TAMIL_BLOCK_PATTERN.search(text))


def is_tamil_word(token: str) -> bool:
    """Return True if *token* consists entirely of Tamil script characters."""
    return bool(_PURE_TAMIL_TOKEN_PATTERN.match(token))


def is_english_word(token: str) -> bool:
    """Return True if *token* consists entirely of ASCII alphabetic characters."""
    return bool(_ASCII_ALPHA_TOKEN_PATTERN.match(token))




_LOGGER_CONFIGURED = False


def setup_logger(name: str, log_file: Path = config.DEFAULT_LOG_FILE,
                  verbose: bool = False) -> logging.Logger:
    """Create (or fetch) a module-level logger writing to console + file.

    Parameters
    ----------
    name:
        Logger name, conventionally ``__name__`` of the calling module.
    log_file:
        Path to the shared ``cleaning.log`` file. Parent directories are
        created automatically.
    verbose:
        When True, console output is set to DEBUG; otherwise INFO.

    Returns
    -------
    logging.Logger
        A ready-to-use logger. Calling this multiple times is safe --
        handlers are only attached once per process.
    """
    global _LOGGER_CONFIGURED

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    root_logger = logging.getLogger("text_cleaner")
    if not _LOGGER_CONFIGURED:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_handler.setFormatter(formatter)

        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.propagate = False

        _LOGGER_CONFIGURED = True

    return logger


@contextmanager
def timed_block(logger: logging.Logger, description: str) -> Iterator[None]:
    """Context manager that logs how long a block of code took to run.

    Example
    -------
    >>> with timed_block(logger, "cleaning dataset"):
    ...     do_work()
    """
    start = time.perf_counter()
    logger.debug("Starting: %s", description)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("%s completed in %.3f seconds", description, elapsed)
