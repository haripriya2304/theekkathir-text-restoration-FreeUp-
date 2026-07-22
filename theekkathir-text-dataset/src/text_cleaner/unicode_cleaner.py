"""
unicode_cleaner.py
===================

Removes Unicode noise commonly introduced by OCR / PDF-to-text
conversion pipelines: non-breaking spaces, zero-width characters, and
byte-order marks. Also applies NFC Unicode normalization so that
visually identical Tamil glyphs are represented consistently.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from text_cleaner import config
from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class UnicodeCleanStats:
    """Counts collected during a single :meth:`UnicodeCleaner.clean` call."""

    non_breaking_spaces_replaced: int = 0
    zero_width_chars_removed: int = 0

    @property
    def total_removed(self) -> int:
        return self.non_breaking_spaces_replaced + self.zero_width_chars_removed


class UnicodeCleaner:
    """Strips invisible/noisy Unicode characters from raw article text."""

    def __init__(self) -> None:
        zero_width_escaped = "".join(re.escape(ch) for ch in config.ZERO_WIDTH_CHARS)
        self._zero_width_pattern = re.compile(f"[{zero_width_escaped}]")
        self._nbsp_pattern = re.compile(re.escape(config.NON_BREAKING_SPACE))
        self.last_stats = UnicodeCleanStats()

    def clean(self, text: str) -> str:
        """Return *text* with Unicode noise removed and normalized to NFC.

        Steps performed (in order):
            1. Replace non-breaking spaces (``\\xa0``) with regular spaces.
            2. Strip zero-width characters (ZWSP, ZWNJ, ZWJ, BOM, word joiner).
            3. Apply Unicode NFC normalization so composed/decomposed
               Tamil glyph sequences are made consistent.

        Parameters
        ----------
        text:
            Raw article text, possibly containing Unicode noise.

        Returns
        -------
        str
            Cleaned text. Whitespace is *not* collapsed here -- that is
            the responsibility of :mod:`text_cleaner.space_normalizer`.
        """
        if not text:
            self.last_stats = UnicodeCleanStats()
            return text

        stats = UnicodeCleanStats()

        nbsp_count = len(self._nbsp_pattern.findall(text))
        text = self._nbsp_pattern.sub(" ", text)
        stats.non_breaking_spaces_replaced = nbsp_count

        zw_count = len(self._zero_width_pattern.findall(text))
        text = self._zero_width_pattern.sub("", text)
        stats.zero_width_chars_removed = zw_count

        text = unicodedata.normalize("NFC", text)

        self.last_stats = stats
        if stats.total_removed:
            logger.debug(
                "UnicodeCleaner removed %d noisy character(s) "
                "(nbsp=%d, zero-width=%d)",
                stats.total_removed,
                stats.non_breaking_spaces_replaced,
                stats.zero_width_chars_removed,
            )
        return text
