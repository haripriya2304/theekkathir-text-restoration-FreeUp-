"""
spell_validator.py
===================

Final safety net for the restoration engine: validates that a
restored (merged) Tamil word is actually plausible before it is
allowed to replace the original split fragments. This prevents the
engine from ever *introducing* incorrect Tamil words into the dataset.
"""

from __future__ import annotations

import re

from text_cleaner import config
from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.frequency_analyzer import FrequencyAnalyzer
from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)

#: A structurally valid Tamil word must start with a consonant, vowel,
#: or independent vowel sign -- never with a *dependent* vowel sign or
#: virama/pulli in isolation (those can only follow a consonant).
_DEPENDENT_SIGNS_START_PATTERN = re.compile(
    r"^[\u0BBE-\u0BCD\u0BD7]"  # dependent vowel signs, virama, au length mark
)


class SpellValidator:
    """Validates whether a candidate Tamil word should be accepted.

    A word is accepted if either:
        * it exists verbatim in the Tamil dictionary, OR
        * (when `require_dictionary_or_frequency` is True) it appears
          in the dataset at least `min_frequency_if_unlisted` times,
          which is treated as corroborating evidence it's a real word.

    In all cases the word must also pass a lightweight structural
    check (must not begin with a dependent vowel sign or virama, since
    such sequences are never valid at the start of a Tamil word).
    """

    def __init__(
        self,
        dictionary_loader: DictionaryLoader = None,  # type: ignore[assignment]
        frequency_analyzer: FrequencyAnalyzer = None,  # type: ignore[assignment]
        validator_config: config.SpellValidatorConfig = config.DEFAULT_SPELL_VALIDATOR_CONFIG,
    ) -> None:
        self.dictionary_loader = dictionary_loader or DictionaryLoader()
        self.frequency_analyzer = frequency_analyzer
        self.validator_config = validator_config

    def _is_structurally_valid(self, word: str) -> bool:
        """Reject words that could never be valid Tamil (cheap sanity check)."""
        if not word:
            return False
        if _DEPENDENT_SIGNS_START_PATTERN.match(word):
            return False
        return True

    def validate(self, word: str) -> bool:
        """Return True if *word* should be accepted as a valid Tamil word.

        Parameters
        ----------
        word:
            Candidate word (typically the output of a merge decision
            made by the restoration engine).

        Returns
        -------
        bool
            True if the word passes validation and may safely replace
            the original text fragments; False if the restoration
            should be rejected and the original fragments kept as-is.
        """
        if not self._is_structurally_valid(word):
            logger.debug("Rejected '%s': fails structural validity check", word)
            return False

        if self.dictionary_loader.contains(word):
            return True

        if not self.validator_config.require_dictionary_or_frequency:
            # Dictionary-only mode requested no fallback -- reject.
            logger.debug("Rejected '%s': not found in dictionary", word)
            return False

        if self.frequency_analyzer is not None:
            freq = self.frequency_analyzer.get_frequency(word)
            if freq >= self.validator_config.min_frequency_if_unlisted:
                logger.debug(
                    "Accepted '%s' via frequency evidence (freq=%d)", word, freq
                )
                return True

        logger.debug("Rejected '%s': not in dictionary and insufficient frequency", word)
        return False
