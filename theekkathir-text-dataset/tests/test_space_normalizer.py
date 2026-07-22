"""Unit tests for text_cleaner.space_normalizer."""

from text_cleaner.space_normalizer import SpaceNormalizer


def test_collapses_multiple_spaces():
    normalizer = SpaceNormalizer()
    result = normalizer.normalize("தமிழ்        மொழி")
    assert result == "தமிழ் மொழி"


def test_strips_leading_and_trailing_whitespace():
    normalizer = SpaceNormalizer()
    result = normalizer.normalize("   தமிழ் மொழி   ")
    assert result == "தமிழ் மொழி"


def test_normalizes_tabs_and_newlines():
    normalizer = SpaceNormalizer()
    result = normalizer.normalize("தமிழ்\t\nமொழி")
    assert result == "தமிழ் மொழி"


def test_already_normalized_text_is_unchanged():
    normalizer = SpaceNormalizer()
    text = "தமிழ் மொழி"
    assert normalizer.normalize(text) == text


def test_empty_string():
    normalizer = SpaceNormalizer()
    assert normalizer.normalize("") == ""
