"""
Tamil Text Restoration Engine
==============================

A modular text-cleaning and restoration toolkit built for the
Theekkathir Tamil News Dataset.

The package removes Unicode noise, strips stray English tokens,
normalizes whitespace, and intelligently restores Tamil words that
were incorrectly split apart during OCR / PDF-to-text conversion.

Public API
----------
The most common entry point is :class:`~text_cleaner.restoration_engine.RestorationEngine`,
which wires together every cleaning stage into a single pipeline via
:func:`~text_cleaner.restoration_engine.RestorationEngine.clean_article`.

Example
-------
>>> from text_cleaner.restoration_engine import RestorationEngine
>>> engine = RestorationEngine()
>>> engine.clean_article("தமிழ்\\xa0மொழி முதலமை ச்சர்")
'தமிழ் மொழி முதலமைச்சர்'
"""

__version__ = "1.0.0"
