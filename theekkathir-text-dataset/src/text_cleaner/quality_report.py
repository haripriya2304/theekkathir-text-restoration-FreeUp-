"""
quality_report.py
==================

Aggregates per-article cleaning statistics across an entire dataset
run and writes a ``quality_report.json`` summarising the effectiveness
of the cleaning pipeline.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from text_cleaner import config
from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class QualityReport:
    """Accumulates dataset-wide cleaning statistics.

    Call :meth:`start` once before processing, :meth:`record_article`
    once per article, then :meth:`finalize` and :meth:`save` when done.
    """

    total_articles: int = 0
    unicode_removed: int = 0
    english_words_removed: int = 0
    words_restored: int = 0
    unknown_words: int = 0
    cleaning_percentage: float = 0.0
    average_confidence: float = 0.0
    execution_time_seconds: float = 0.0

    _confidence_sum: float = field(default=0.0, repr=False)
    _confidence_count: int = field(default=0, repr=False)
    _start_time: float = field(default=0.0, repr=False)
    _articles_changed: int = field(default=0, repr=False)

    def start(self) -> None:
        """Mark the beginning of a dataset processing run."""
        self._start_time = time.perf_counter()
        logger.info("Quality report timer started")

    def record_article(
        self,
        *,
        unicode_removed: int,
        english_removed: int,
        words_restored: int,
        unknown_words: int,
        average_confidence: float,
        changed: bool,
    ) -> None:
        """Record statistics for a single processed article.

        Parameters
        ----------
        unicode_removed:
            Count of Unicode noise characters removed from this article.
        english_removed:
            Count of English noise tokens removed from this article.
        words_restored:
            Count of word pairs merged during restoration.
        unknown_words:
            Count of merge candidates rejected by the spell validator.
        average_confidence:
            Mean confidence score across merge decisions for this article.
        changed:
            Whether this article's text differed after cleaning.
        """
        self.total_articles += 1
        self.unicode_removed += unicode_removed
        self.english_words_removed += english_removed
        self.words_restored += words_restored
        self.unknown_words += unknown_words

        if average_confidence:
            self._confidence_sum += average_confidence
            self._confidence_count += 1

        if changed:
            self._articles_changed += 1

    def finalize(self) -> None:
        """Compute derived metrics once all articles have been recorded."""
        self.execution_time_seconds = round(time.perf_counter() - self._start_time, 4)

        if self.total_articles:
            self.cleaning_percentage = round(
                (self._articles_changed / self.total_articles) * 100, 2
            )
        else:
            self.cleaning_percentage = 0.0

        if self._confidence_count:
            self.average_confidence = round(
                self._confidence_sum / self._confidence_count, 4
            )
        else:
            self.average_confidence = 0.0

        logger.info(
            "Quality report finalized: %d articles, %.2f%% cleaned, "
            "%d words restored, %.3fs elapsed",
            self.total_articles,
            self.cleaning_percentage,
            self.words_restored,
            self.execution_time_seconds,
        )

    def to_dict(self) -> dict:
        """Return the public (non-underscore) fields as a plain dict."""
        data = asdict(self)
        return {k: v for k, v in data.items() if not k.startswith("_")}

    def save(self, path: Path = config.DEFAULT_QUALITY_REPORT_PATH) -> None:
        """Write the report to *path* as pretty-printed JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)
        logger.info("Quality report saved to %s", path)
