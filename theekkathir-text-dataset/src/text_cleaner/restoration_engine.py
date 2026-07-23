"""
restoration_engine.py
======================

The core of the Tamil Text Restoration Engine.

Corrupted OCR/PDF extraction frequently splits a single Tamil word
into two adjacent tokens, e.g. ``முதலமை ச்சர்`` instead of
``முதலமைச்சர்``. This module decides -- for every pair of adjacent
Tamil tokens -- whether they should be merged back together, using a
weighted combination of three signals:

    1. **Dictionary score**  -- does the merged word exist in the
       Tamil dictionary?
    2. **Frequency score**   -- how common is the merged word (vs. the
       individual fragments) in the dataset being cleaned?
    3. **Context score**     -- how common is the merged word as a
       *bigram* alongside its neighbouring words (captures phrases
       like ``தமிழக முதலமைச்சர்``)?

The engine also runs the full cleaning pipeline end-to-end via
:meth:`RestorationEngine.clean_article`, chaining the Unicode cleaner,
English cleaner, space normalizer, word restoration, and spell
validation in the order required by the project pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from text_cleaner import config
from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.english_cleaner import EnglishCleaner
from text_cleaner.frequency_analyzer import FrequencyAnalyzer
from text_cleaner.space_normalizer import SpaceNormalizer
from text_cleaner.spell_validator import SpellValidator
from text_cleaner.unicode_cleaner import UnicodeCleaner
from text_cleaner.utils import is_tamil_word, setup_logger

logger = setup_logger(__name__)


@dataclass
class MergeDecision:
    """Detailed record of a single merge/split decision, useful for
    debugging, testing, and quality reporting."""

    left: str
    right: str
    merged_candidate: str
    merged_score: float
    split_score: float
    merged: bool
    rejected_by_spell_validator: bool = False


@dataclass
class RestorationStats:
    """Aggregate counters collected while restoring a single article."""

    pairs_considered: int = 0
    words_restored: int = 0
    decisions: List[MergeDecision] = field(default_factory=list)
    average_confidence: float = 0.0

    def record(self, decision: MergeDecision) -> None:
        self.pairs_considered += 1
        self.decisions.append(decision)
        if decision.merged:
            self.words_restored += 1

    def finalize(self) -> None:
        if self.decisions:
            self.average_confidence = sum(
                d.merged_score for d in self.decisions
            ) / len(self.decisions)


class RestorationEngine:
    """Restores split Tamil words and runs the full cleaning pipeline.

    Parameters
    ----------
    dictionary_loader:
        Provides the known-word set used for dictionary scoring.
        Defaults to loading ``resources/tamil_dictionary.txt``.
    frequency_analyzer:
        Provides unigram/bigram frequency statistics. If not supplied
        (or not yet fitted via :meth:`FrequencyAnalyzer.build_from_texts`),
        frequency and context scores gracefully degrade to zero rather
        than raising an error.
    weights:
        Relative weighting of the dictionary/frequency/context signals.
    """

    def __init__(
        self,
        dictionary_loader: Optional[DictionaryLoader] = None,
        frequency_analyzer: Optional[FrequencyAnalyzer] = None,
        weights: config.ScoringWeights = config.DEFAULT_SCORING_WEIGHTS,
        spell_validator_config: config.SpellValidatorConfig = config.DEFAULT_SPELL_VALIDATOR_CONFIG,
    ) -> None:
        self.dictionary_loader = dictionary_loader or DictionaryLoader()
        self.frequency_analyzer = frequency_analyzer or FrequencyAnalyzer()
        self.weights = weights

        self.unicode_cleaner = UnicodeCleaner()
        self.english_cleaner = EnglishCleaner()
        self.space_normalizer = SpaceNormalizer()
        self.spell_validator = SpellValidator(
            dictionary_loader=self.dictionary_loader,
            frequency_analyzer=self.frequency_analyzer,
            validator_config=spell_validator_config,
        )

        self.last_stats = RestorationStats()


    def _dictionary_score(self, merged: str, left: str, right: str) -> float:
        """1.0 if the merged word is known; small credit if both halves
        are independently known (evidence *against* merging)."""
        if self.dictionary_loader.contains(merged):
            return 1.0
        return 0.0

    def _frequency_score(self, merged: str, left: str, right: str) -> float:
        """Compares merged-word frequency against the fragments' frequency
        using a smoothed log-ratio, squashed into [0, 1] via a sigmoid.
        """
        if not self.frequency_analyzer.is_fitted:
            return 0.0

        merged_freq = self.frequency_analyzer.get_frequency(merged)
        fragment_freq = (
            self.frequency_analyzer.get_frequency(left)
            + self.frequency_analyzer.get_frequency(right)
        )

        
        ratio = (merged_freq + 1) / (fragment_freq + 1)
        score = 1 / (1 + math.exp(-math.log(ratio)))
        return score

    def _context_score(
        self, merged: str, prev_token: Optional[str], next_token: Optional[str]
    ) -> float:
        """Bigram evidence: does the merged word commonly appear next to
        its neighbours in the dataset? (e.g. தமிழக + முதலமைச்சர்)."""
        if not self.frequency_analyzer.is_fitted:
            return 0.0

        signals = []
        if prev_token is not None and is_tamil_word(prev_token):
            freq = self.frequency_analyzer.get_bigram_frequency(prev_token, merged)
            signals.append(freq)
        if next_token is not None and is_tamil_word(next_token):
            freq = self.frequency_analyzer.get_bigram_frequency(merged, next_token)
            signals.append(freq)

        if not signals:
            return 0.0

        total = sum(signals)
        return 1 - math.exp(-total / 2.0)

    def compute_confidence(
        self,
        left: str,
        right: str,
        prev_token: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> MergeDecision:
        """Score the merge candidate formed by joining *left* + *right*.

        Returns a :class:`MergeDecision` describing both the merged and
        split scores and the resulting boolean decision (before spell
        validation is applied).
        """
        merged_candidate = left + right

        if len(merged_candidate) > config.MAX_MERGED_WORD_LENGTH:
            return MergeDecision(
                left=left,
                right=right,
                merged_candidate=merged_candidate,
                merged_score=0.0,
                split_score=1.0,
                merged=False,
            )

        dict_score = self._dictionary_score(merged_candidate, left, right)
        freq_score = self._frequency_score(merged_candidate, left, right)
        ctx_score = self._context_score(merged_candidate, prev_token, next_token)

        merged_score = (
            self.weights.dictionary * dict_score
            + self.weights.frequency * freq_score
            + self.weights.context * ctx_score
        )

    
        left_known = self.dictionary_loader.contains(left)
        right_known = self.dictionary_loader.contains(right)
        split_dict_score = 1.0 if (left_known and right_known) else 0.0
        split_score = self.weights.dictionary * split_dict_score

        should_merge = (merged_score - split_score) > config.MERGE_DECISION_MARGIN

        return MergeDecision(
            left=left,
            right=right,
            merged_candidate=merged_candidate,
            merged_score=round(merged_score, 4),
            split_score=round(split_score, 4),
            merged=should_merge,
        )

    

    def restore(self, text: str) -> str:
        """Restore split Tamil words within *text*.

        Adjacent Tamil-script tokens are evaluated pairwise (left to
        right, single pass) and merged when the confidence score favours
        merging *and* the resulting word passes spell validation.

        Parameters
        ----------
        text:
            Text that has already been Unicode-cleaned, had English
            noise removed, and had whitespace normalized.

        Returns
        -------
        str
            Text with eligible word pairs merged back together.
        """
        stats = RestorationStats()

        if not text:
            self.last_stats = stats
            return text

        tokens = text.split(" ")
        result: List[str] = []
        i = 0
        n = len(tokens)

        while i < n:
            current = tokens[i]

            if (
                i + 1 < n
                and is_tamil_word(current)
                and is_tamil_word(tokens[i + 1])
                and len(current) >= config.MIN_FRAGMENT_LENGTH_FOR_MERGE
                and len(tokens[i + 1]) >= config.MIN_FRAGMENT_LENGTH_FOR_MERGE
            ):
                right = tokens[i + 1]
                prev_token = result[-1] if result else None
                next_token = tokens[i + 2] if i + 2 < n else None

                decision = self.compute_confidence(current, right, prev_token, next_token)

                if decision.merged:
                    if self.spell_validator.validate(decision.merged_candidate):
                        result.append(decision.merged_candidate)
                        stats.record(decision)
                        i += 2
                        continue
                    else:
                        decision.merged = False
                        decision.rejected_by_spell_validator = True

                stats.record(decision)

            result.append(current)
            i += 1

        stats.finalize()
        self.last_stats = stats

        if stats.words_restored:
            logger.debug(
                "RestorationEngine merged %d word pair(s) out of %d considered",
                stats.words_restored,
                stats.pairs_considered,
            )

        return " ".join(result)

    

    def clean_article(self, text: str) -> str:
        """Run the complete cleaning pipeline on a single article.

        Order: Unicode cleaner -> English cleaner -> space normalizer
        -> restoration engine -> space normalizer (final pass, since
        merges can change spacing).

        Parameters
        ----------
        text:
            Raw article text as scraped/extracted.

        Returns
        -------
        str
            Fully cleaned and restored article text.
        """
        if text is None:
            return text

        text = self.unicode_cleaner.clean(text)
        text = self.english_cleaner.clean(text)
        text = self.space_normalizer.normalize(text)
        text = self.restore(text)
        text = self.space_normalizer.normalize(text)
        return text
