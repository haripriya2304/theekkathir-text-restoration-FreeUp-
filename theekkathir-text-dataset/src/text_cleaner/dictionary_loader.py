"""
dictionary_loader.py
=====================

Loads the Tamil word dictionary used by the restoration engine and
spell validator to decide whether a merged/split word is a real word.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

from text_cleaner import config
from text_cleaner.utils import setup_logger

logger = setup_logger(__name__)


class DictionaryLoader:
    """Loads a newline-delimited Tamil word list into an in-memory set.

    The dictionary file supports blank lines and ``#``-prefixed comment
    lines, both of which are ignored.
    """

    def __init__(self, path: Path = config.DEFAULT_DICTIONARY_PATH) -> None:
        self.path = Path(path)
        self._cache: Set[str] = None  # type: ignore[assignment]

    def load(self, force_reload: bool = False) -> Set[str]:
        """Load (or return the cached) dictionary word set.

        Parameters
        ----------
        force_reload:
            When True, re-reads the file from disk even if a cached
            copy already exists.

        Returns
        -------
        Set[str]
            The set of known Tamil words.

        Raises
        ------
        FileNotFoundError
            If the dictionary file does not exist on disk.
        """
        if self._cache is not None and not force_reload:
            return self._cache

        if not self.path.exists():
            raise FileNotFoundError(
                f"Tamil dictionary not found at '{self.path}'. "
                "Provide a valid path via DictionaryLoader(path=...) "
                "or place a word list at resources/tamil_dictionary.txt."
            )

        words: Set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words.add(line)

        logger.info("Loaded %d Tamil dictionary entries from %s", len(words), self.path)
        self._cache = words
        return words

    def contains(self, word: str) -> bool:
        """Return True if *word* exists in the loaded dictionary."""
        return word in self.load()

    def add_words(self, words: Set[str]) -> None:
        """Extend the in-memory dictionary with additional known-good words.

        Useful for injecting words discovered via high-confidence
        frequency analysis without editing the dictionary file itself.
        """
        current = self.load()
        current.update(words)
        self._cache = current
