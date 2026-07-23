"""
space_normalizer.py
====================

Collapses runs of whitespace produced by earlier cleaning stages (or
present in the raw scrape) into single spaces, and trims leading /
trailing whitespace.
"""

from __future__ import annotations

import re

from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)


class SpaceNormalizer:
    """Normalizes whitespace in article text."""

    
    _WHITESPACE_RUN_PATTERN = re.compile(r"\s+")

    def normalize(self, text: str) -> str:
        """Collapse whitespace runs to a single space and trim the ends.

        Parameters
        ----------
        text:
            Text that may contain multiple/irregular spaces.

        Returns
        -------
        str
            Text with whitespace normalized to single ASCII spaces.
        """
        if not text:
            return text

        normalized = self._WHITESPACE_RUN_PATTERN.sub(" ", text).strip()
        if normalized != text:
            logger.debug("SpaceNormalizer normalized whitespace")
        return normalized
