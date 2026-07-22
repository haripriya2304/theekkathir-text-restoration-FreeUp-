"""
config.py
=========

Centralised, reusable configuration for the Tamil Text Restoration Engine.

Nothing in the rest of the codebase should hardcode paths, thresholds,
or word lists -- everything tunable lives here so the pipeline can be
re-configured (or re-used on a different dataset) without touching
module internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set


# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------

#: Root of the repository (three levels up from this file:
#: src/text_cleaner/config.py -> src/text_cleaner -> src -> <repo root>)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

RESOURCES_DIR: Path = PROJECT_ROOT / "resources"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
LOGS_DIR: Path = PROJECT_ROOT / "logs"

DEFAULT_DICTIONARY_PATH: Path = RESOURCES_DIR / "tamil_dictionary.txt"
DEFAULT_LOG_FILE: Path = LOGS_DIR / "cleaning.log"
DEFAULT_QUALITY_REPORT_PATH: Path = OUTPUT_DIR / "quality_report.json"


# ---------------------------------------------------------------------------
# Unicode noise characters
# ---------------------------------------------------------------------------

#: Characters that should be stripped outright (zero-width / BOM / NBSP).
#: NBSP (\xa0) is treated specially -- it is *replaced* with a normal
#: space rather than deleted, since it usually separates real words.
ZERO_WIDTH_CHARS: Set[str] = {
    "\u200b",  # zero width space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\ufeff",  # byte order mark / zero width no-break space
    "\u2060",  # word joiner
}

NON_BREAKING_SPACE: str = "\xa0"


# ---------------------------------------------------------------------------
# English noise tokens
# ---------------------------------------------------------------------------

#: Known "junk" English tokens that frequently leak into scraped Tamil
#: news articles (section labels, banners, etc). Matching is
#: case-insensitive.
ENGLISH_NOISE_WORDS: Set[str] = {
    "news",
    "update",
    "updates",
    "live",
    "breaking",
    "video",
    "videos",
    "advertisement",
    "advertisment",  # common misspelling seen in scraped data
    "ad",
    "ads",
    "sponsored",
    "photo",
    "photos",
    "gallery",
    "exclusive",
    "watch",
    "read",
    "more",
    "trending",
}

#: If True, *every* isolated ASCII-alphabetic token is stripped
#: (not just the curated noise list above). If False, only tokens
#: found in ENGLISH_NOISE_WORDS are removed, which is safer when the
#: article legitimately contains English proper nouns.
STRIP_ALL_ISOLATED_ENGLISH: bool = False

#: Tokens that must never be removed even if they are ASCII, because
#: they carry meaning (numerals mixed with units, abbreviations, etc).
ENGLISH_WHITELIST: Set[str] = {
    "AI",
    "IT",
    "TV",
    "AC",
    "UPI",
    "GST",
    "CM",
    "PM",
}


# ---------------------------------------------------------------------------
# Restoration engine scoring weights
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringWeights:
    """Relative weight given to each signal when scoring a merge candidate."""

    dictionary: float = 0.5
    frequency: float = 0.3
    context: float = 0.2

    def __post_init__(self) -> None:
        total = self.dictionary + self.frequency + self.context
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"ScoringWeights must sum to 1.0, got {total}")


DEFAULT_SCORING_WEIGHTS = ScoringWeights()

#: Minimum length (in Tamil characters) a fragment must have before we
#: even consider merging it with its neighbour. This avoids merging
#: two perfectly valid, unrelated short words.
MIN_FRAGMENT_LENGTH_FOR_MERGE: int = 1

#: Maximum length of a merged candidate word. Guards against runaway
#: merges across long stretches of legitimately separate words.
MAX_MERGED_WORD_LENGTH: int = 25

#: A merge is only accepted when merged_score - split_score exceeds
#: this margin (avoids flip-flopping on near-tied scores).
MERGE_DECISION_MARGIN: float = 0.05


# ---------------------------------------------------------------------------
# Spell validation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpellValidatorConfig:
    """Configuration for :class:`text_cleaner.spell_validator.SpellValidator`."""

    #: Require the restored word to exist in the dictionary OR have a
    #: dataset frequency above `min_frequency_if_unlisted` to be accepted.
    require_dictionary_or_frequency: bool = True
    min_frequency_if_unlisted: int = 3


DEFAULT_SPELL_VALIDATOR_CONFIG = SpellValidatorConfig()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Parquet / CLI defaults
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineConfig:
    """High level knobs exposed to the CLI (main.py)."""

    text_column: str = "content"
    dictionary_path: Path = DEFAULT_DICTIONARY_PATH
    quality_report_path: Path = DEFAULT_QUALITY_REPORT_PATH
    scoring_weights: ScoringWeights = field(default_factory=lambda: DEFAULT_SCORING_WEIGHTS)
    spell_validator_config: SpellValidatorConfig = field(
        default_factory=lambda: DEFAULT_SPELL_VALIDATOR_CONFIG
    )
