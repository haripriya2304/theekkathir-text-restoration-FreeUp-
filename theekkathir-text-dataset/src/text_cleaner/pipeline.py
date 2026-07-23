"""
pipeline.py
===========

Shared dataset-level processing logic, used by both the CLI
(``main.py``) and the Streamlit UI (``app.py``) so the two entry
points can never drift apart.

The core function, :func:`process_dataframe`, takes a pandas
DataFrame plus the name of the text column to clean, runs every row
through a :class:`~text_cleaner.restoration_engine.RestorationEngine`,
and returns both the cleaned DataFrame and a fully populated
:class:`~text_cleaner.quality_report.QualityReport`.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

import pandas as pd

from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.frequency_analyzer import FrequencyAnalyzer
from text_cleaner.quality_report import QualityReport
from text_cleaner.restoration_engine import RestorationEngine
from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)

ProgressCallback = Callable[[int, int], None]


def process_dataframe(
    df: pd.DataFrame,
    text_column: str,
    engine: Optional[RestorationEngine] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Tuple[pd.DataFrame, QualityReport]:
    """Run the full cleaning pipeline over every row of *df*.

    Parameters
    ----------
    df:
        Input dataset. Must contain *text_column*.
    text_column:
        Name of the column holding raw article text.
    engine:
        A pre-configured :class:`RestorationEngine`. If omitted, a
        default engine (default dictionary, dataset-fitted frequency
        analyzer) is created automatically.
    progress_callback:
        Optional callback invoked as ``progress_callback(i, total)``
        after each row is processed, for UI progress reporting.

    Returns
    -------
    Tuple[pandas.DataFrame, QualityReport]
        The cleaned DataFrame (a copy -- the input is not mutated) and
        a finalized quality report describing the run.

    Raises
    ------
    KeyError
        If *text_column* is not present in *df*.
    """
    if text_column not in df.columns:
        raise KeyError(
            f"Column '{text_column}' not found in dataset. "
            f"Available columns: {list(df.columns)}"
        )

    if engine is None:
        frequency_analyzer = FrequencyAnalyzer()
        frequency_analyzer.build_from_texts(df[text_column].fillna("").astype(str))
        engine = RestorationEngine(
            dictionary_loader=DictionaryLoader(), frequency_analyzer=frequency_analyzer
        )
    elif not engine.frequency_analyzer.is_fitted:
    
        engine.frequency_analyzer.build_from_texts(df[text_column].fillna("").astype(str))

    report = QualityReport()
    report.start()

    cleaned_texts = []
    total = len(df)

    for i, original in enumerate(df[text_column].fillna("").astype(str), start=1):
        engine.unicode_cleaner.clean(original)
        unicode_removed = engine.unicode_cleaner.last_stats.total_removed

        cleaned = engine.clean_article(original)
        english_removed = engine.english_cleaner.last_stats.english_words_removed
        words_restored = engine.last_stats.words_restored
        unknown_words = sum(
            1 for d in engine.last_stats.decisions if d.rejected_by_spell_validator
        )

        report.record_article(
            unicode_removed=unicode_removed,
            english_removed=english_removed,
            words_restored=words_restored,
            unknown_words=unknown_words,
            average_confidence=engine.last_stats.average_confidence,
            changed=(cleaned != original),
        )
        cleaned_texts.append(cleaned)

        if progress_callback is not None:
            progress_callback(i, total)

    report.finalize()

    cleaned_df = df.copy()
    cleaned_df[text_column] = cleaned_texts

    logger.info(
        "process_dataframe finished: %d rows, %d words restored, %.2f%% changed",
        report.total_articles,
        report.words_restored,
        report.cleaning_percentage,
    )

    return cleaned_df, report
