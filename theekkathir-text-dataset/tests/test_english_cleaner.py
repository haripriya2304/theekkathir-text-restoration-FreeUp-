"""Unit tests for text_cleaner.english_cleaner."""

from text_cleaner.english_cleaner import EnglishCleaner


def test_removes_curated_noise_word():
    cleaner = EnglishCleaner()
    result = cleaner.clean("தமிழ் News Update")
    assert result == "தமிழ்"


def test_removes_multiple_noise_words():
    cleaner = EnglishCleaner()
    result = cleaner.clean("Breaking தமிழ் மொழி LIVE")
    assert result == "தமிழ் மொழி"


def test_does_not_touch_tamil_text():
    cleaner = EnglishCleaner()
    text = "தமிழ் மொழி வளர்ச்சி"
    assert cleaner.clean(text) == text


def test_whitelisted_english_token_is_kept():
    cleaner = EnglishCleaner()
    result = cleaner.clean("தமிழ்நாடு CM அறிவிப்பு")
    assert "CM" in result


def test_non_noise_english_word_is_kept_by_default():
    cleaner = EnglishCleaner()
    # "Chennai" is not in the curated noise list and strip_all is off by default.
    result = cleaner.clean("தமிழ் Chennai மொழி")
    assert "Chennai" in result


def test_strip_all_isolated_english_mode():
    cleaner = EnglishCleaner(strip_all_isolated_english=True)
    result = cleaner.clean("தமிழ் Chennai மொழி")
    assert "Chennai" not in result
    assert result == "தமிழ் மொழி"


def test_stats_track_removed_tokens():
    cleaner = EnglishCleaner()
    cleaner.clean("தமிழ் News Update")
    assert cleaner.last_stats.english_words_removed == 2
    assert "News" in cleaner.last_stats.removed_tokens


def test_empty_string():
    cleaner = EnglishCleaner()
    assert cleaner.clean("") == ""
