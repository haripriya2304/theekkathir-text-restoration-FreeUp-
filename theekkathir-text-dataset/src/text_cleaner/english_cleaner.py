"""
english_cleaner.py
===================

Removes stray isolated English tokens (section labels, banner text
such as "News", "LIVE", "Advertisement") that leak into scraped Tamil
articles, without disturbing genuine Tamil content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from text_cleaner import config
from text_cleaner.utils import is_english_word, setup_logger

logger = setup_logger(__name__)


@dataclass
class EnglishCleanStats:
    """Counts collected during a single :meth:`EnglishCleaner.clean` call."""

    english_words_removed: int = 0
    removed_tokens: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.removed_tokens is None:
            self.removed_tokens = []


class EnglishCleaner:
    """Removes isolated English noise words from Tamil article text.

    Only *whole tokens* (whitespace-delimited) that are entirely ASCII
    alphabetic are considered candidates for removal -- this guarantees
    Tamil text is never touched, since Tamil characters fall outside
    the ASCII range entirely.
    """

    def __init__(
        self,
        noise_words: Set[str] = None,  # type: ignore[assignment]
        whitelist: Set[str] = None,  # type: ignore[assignment]
        strip_all_isolated_english: bool = config.STRIP_ALL_ISOLATED_ENGLISH,
    ) -> None:
        self.noise_words = {w.lower() for w in (noise_words or config.ENGLISH_NOISE_WORDS)}
        self.whitelist = {w.lower() for w in (whitelist or config.ENGLISH_WHITELIST)}
        self.strip_all_isolated_english = strip_all_isolated_english
        self.last_stats = EnglishCleanStats()

    def _should_remove(self, token: str) -> bool:
        """Decide whether a single whitespace-delimited *token* should go."""
        # Strip common surrounding punctuation before comparing, but keep
        # the original token when re-inserting so we don't mangle text
        # that mixes punctuation with Tamil (rare, but be safe).
        stripped = token.strip(".,!?:;()[]\"'")
        if not stripped or not is_english_word(stripped):
            return False
        lowered = stripped.lower()
        if lowered in self.whitelist:
            return False
        if self.strip_all_isolated_english:
            return True
        return lowered in self.noise_words

    def clean(self, text: str) -> str:
        """Remove isolated English noise tokens from *text*.

        Parameters
        ----------
        text:
            Article text, already Unicode-cleaned.

        Returns
        -------
        str
            Text with matching English tokens removed. Spacing around
            removed tokens is left for :mod:`text_cleaner.space_normalizer`
            to clean up.
        """
        if not text:
            self.last_stats = EnglishCleanStats()
            return text

        tokens = text.split(" ")
        kept_tokens = []
        removed = []

        for token in tokens:
            if token == "":
                kept_tokens.append(token)
                continue
            if self._should_remove(token):
                removed.append(token)
                continue
            kept_tokens.append(token)

        cleaned = " ".join(kept_tokens)
        self.last_stats = EnglishCleanStats(
            english_words_removed=len(removed), removed_tokens=removed
        )
        if removed:
            logger.debug("EnglishCleaner removed tokens: %s", removed)
        return cleaned
