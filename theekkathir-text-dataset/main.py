#!/usr/bin/env python3
"""
main.py
=======

Command-line entry point for the Tamil Text Restoration Engine.

Usage
-----
    python main.py input.parquet output.parquet
    python main.py input.parquet output.parquet --report
    python main.py input.parquet output.parquet --report --verbose
    python main.py input.parquet output.parquet --column content

The script reads a Parquet dataset (as produced by the Theekkathir
scraper), runs every article's text column through the full cleaning
pipeline (Unicode cleaning -> English cleaning -> space normalization
-> Tamil word restoration -> spell validation), and writes the cleaned
dataset back out as Parquet.

Passing ``--report`` additionally writes ``output/quality_report.json``
summarising how much cleaning was performed.

For a point-and-click alternative, see ``app.py`` (Streamlit UI):
    streamlit run app.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from text_cleaner import config  
from text_cleaner.dictionary_loader import DictionaryLoader  # noqa: E402
from text_cleaner.frequency_analyzer import FrequencyAnalyzer  # noqa: E402
from text_cleaner.pipeline import process_dataframe  # noqa: E402
from text_cleaner.restoration_engine import RestorationEngine  # noqa: E402
from text_cleaner.utils import setup_logger, timed_block  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments for the cleaning CLI."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Clean and restore corrupted Tamil text in the Theekkathir dataset.",
    )
    parser.add_argument("input", type=Path, help="Path to the input Parquet file.")
    parser.add_argument("output", type=Path, help="Path to write the cleaned Parquet file.")
    parser.add_argument(
        "--column",
        default=config.PipelineConfig.text_column,
        help=f"Name of the text column to clean (default: '{config.PipelineConfig.text_column}').",
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=config.DEFAULT_DICTIONARY_PATH,
        help="Path to the Tamil dictionary word list.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a quality_report.json summarising the cleaning run.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=config.DEFAULT_QUALITY_REPORT_PATH,
        help="Where to write the quality report JSON (implies --report).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG-level) console logging.",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    """Execute the cleaning pipeline according to parsed CLI *args*.

    Returns
    -------
    int
        Process exit code (0 on success, non-zero on failure).
    """
    logger = setup_logger("text_cleaner.cli", verbose=args.verbose)

    if not args.input.exists():
        logger.error("Input file does not exist: %s", args.input)
        return 1

    logger.info("Reading input dataset: %s", args.input)
    try:
        df = pd.read_parquet(args.input)
    except Exception as exc:  
        logger.error("Failed to read input Parquet file: %s", exc)
        return 1

    if args.column not in df.columns:
        logger.error(
            "Column '%s' not found in input dataset. Available columns: %s",
            args.column,
            list(df.columns),
        )
        return 1

    dictionary_loader = DictionaryLoader(path=args.dictionary)
    frequency_analyzer = FrequencyAnalyzer()
    engine = RestorationEngine(
        dictionary_loader=dictionary_loader, frequency_analyzer=frequency_analyzer
    )

    with timed_block(logger, "building frequency statistics"):
        frequency_analyzer.build_from_texts(df[args.column].fillna("").astype(str))

    with timed_block(logger, f"cleaning {len(df)} articles"):
        cleaned_df, report = process_dataframe(df, args.column, engine=engine)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with timed_block(logger, "writing cleaned dataset"):
        cleaned_df.to_parquet(args.output, index=False)
    logger.info("Cleaned dataset written to %s", args.output)

    if args.report or args.report_path != config.DEFAULT_QUALITY_REPORT_PATH:
        report.save(args.report_path)
        logger.info("Quality report written to %s", args.report_path)

    logger.info(
        "Done: %d articles processed, %d words restored, %.2f%% of articles changed.",
        report.total_articles,
        report.words_restored,
        report.cleaning_percentage,
    )
    return 0


def main(argv=None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    exit_code = run(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
