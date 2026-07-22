"""Unit tests for text_cleaner.unicode_cleaner."""

from text_cleaner.unicode_cleaner import UnicodeCleaner


def test_replaces_non_breaking_space_with_regular_space():
    cleaner = UnicodeCleaner()
    result = cleaner.clean("தமிழ்\xa0மொழி")
    assert result == "தமிழ் மொழி"


def test_removes_zero_width_space():
    cleaner = UnicodeCleaner()
    result = cleaner.clean("தமிழ்\u200bமொழி")
    assert "\u200b" not in result


def test_removes_byte_order_mark():
    cleaner = UnicodeCleaner()
    result = cleaner.clean("\ufeffதமிழ் மொழி")
    assert not result.startswith("\ufeff")
    assert result == "தமிழ் மொழி"


def test_removes_multiple_zero_width_characters():
    cleaner = UnicodeCleaner()
    text = "த\u200cமிழ்\u200d மொ\u2060ழி"
    result = cleaner.clean(text)
    for ch in ("\u200c", "\u200d", "\u2060"):
        assert ch not in result


def test_empty_string_returns_empty_string():
    cleaner = UnicodeCleaner()
    assert cleaner.clean("") == ""


def test_clean_text_is_unchanged():
    cleaner = UnicodeCleaner()
    text = "தமிழ் மொழி"
    assert cleaner.clean(text) == text


def test_stats_are_tracked():
    cleaner = UnicodeCleaner()
    cleaner.clean("தமிழ்\xa0மொழி\u200b")
    assert cleaner.last_stats.non_breaking_spaces_replaced == 1
    assert cleaner.last_stats.zero_width_chars_removed == 1
    assert cleaner.last_stats.total_removed == 2
