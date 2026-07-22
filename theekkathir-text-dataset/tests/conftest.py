"""
conftest.py
===========

Ensures ``src/`` is importable as ``text_cleaner`` when running pytest
from the repository root, without requiring the package to be
installed first (e.g. via ``pip install -e .``).
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
