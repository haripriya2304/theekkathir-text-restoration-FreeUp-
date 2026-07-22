"""
frequency_analyzer.py
======================

Builds word- and bigram-frequency statistics across the dataset so the
restoration engine can favour merges that produce common, plausible
Tamil words (and common word *pairs*) over rare or nonsensical ones.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Tuple

from text_cleaner.utils import is_tamil_word, setup_logger

logger = setup_logger(__name__)


class FrequencyAnalyzer:
    """Computes unigram and bigram frequencies for Tamil tokens.

    The analyzer is deliberately dataset-driven rather than relying on
    an external corpus: it learns what "common" looks like directly
    from the Theekkathir dataset being cleaned, which keeps it
    self-contained and dependency-free.
    """

    def __init__(self) -> None:
        self.word_freq: Counter[str] = Counter()
        self.bigram_freq: Counter[Tuple[str, str]] = Counter()
        self._fitted = False

    def build_from_texts(self, texts: Iterable[str]) -> None:
        """Scan an iterable of article texts and accumulate frequencies.

        Parameters
        ----------
        texts:
            Iterable of raw or cleaned article strings. Non-Tamil
            tokens are ignored for the purposes of frequency counting.
        """
        for text in texts:
            if not text:
                continue
            tokens = [t for t in text.split(" ") if t]
            tamil_tokens = [t for t in tokens if is_tamil_word(t)]

            self.word_freq.update(tamil_tokens)
            for a, b in zip(tamil_tokens, tamil_tokens[1:]):
                self.bigram_freq[(a, b)] += 1

        self._fitted = True
        logger.info(
            "FrequencyAnalyzer built stats: %d unique words, %d unique bigrams",
            len(self.word_freq),
            len(self.bigram_freq),
        )

    def get_frequency(self, word: str) -> int:
        """Return how many times *word* was observed in the dataset."""
        return self.word_freq.get(word, 0)

    def get_bigram_frequency(self, word_a: str, word_b: str) -> int:
        """Return how many times the pair *(word_a, word_b)* was observed."""
        return self.bigram_freq.get((word_a, word_b), 0)

    def most_common(self, n: int = 20):
        """Return the *n* most frequent Tamil words observed so far."""
        return self.word_freq.most_common(n)

    def save(self, path: Path) -> None:
        """Persist unigram/bigram frequencies to a JSON file for reuse."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "word_freq": dict(self.word_freq),
            "bigram_freq": {f"{a}\t{b}": count for (a, b), count in self.bigram_freq.items()},
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        logger.info("Saved frequency statistics to %s", path)

    def load(self, path: Path) -> None:
        """Load previously saved unigram/bigram frequencies from JSON."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.word_freq = Counter(payload.get("word_freq", {}))
        self.bigram_freq = Counter()
        for key, count in payload.get("bigram_freq", {}).items():
            a, b = key.split("\t")
            self.bigram_freq[(a, b)] = count
        self._fitted = True
        logger.info("Loaded frequency statistics from %s", path)

    @property
    def is_fitted(self) -> bool:
        """Whether :meth:`build_from_texts` (or :meth:`load`) has run yet."""
        return self._fitted
