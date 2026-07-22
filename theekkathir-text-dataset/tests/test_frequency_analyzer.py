"""Unit tests for text_cleaner.frequency_analyzer."""

import json

from text_cleaner.frequency_analyzer import FrequencyAnalyzer


def test_build_from_texts_counts_unigrams():
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழ் மொழி", "தமிழ் நாடு"])
    assert analyzer.get_frequency("தமிழ்") == 2
    assert analyzer.get_frequency("மொழி") == 1


def test_build_from_texts_counts_bigrams():
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழக முதலமைச்சர் பேசினார்"])
    assert analyzer.get_bigram_frequency("தமிழக", "முதலமைச்சர்") == 1
    assert analyzer.get_bigram_frequency("முதலமைச்சர்", "பேசினார்") == 1


def test_unknown_word_has_zero_frequency():
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழ் மொழி"])
    assert analyzer.get_frequency("இல்லாதசொல்") == 0


def test_is_fitted_flag():
    analyzer = FrequencyAnalyzer()
    assert analyzer.is_fitted is False
    analyzer.build_from_texts(["தமிழ் மொழி"])
    assert analyzer.is_fitted is True


def test_most_common_returns_sorted_words():
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழ் தமிழ் தமிழ் மொழி"])
    top = analyzer.most_common(1)
    assert top[0][0] == "தமிழ்"
    assert top[0][1] == 3


def test_save_and_load_round_trip(tmp_path):
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழக முதலமைச்சர் பேசினார்"])

    save_path = tmp_path / "freq.json"
    analyzer.save(save_path)
    assert save_path.exists()

    reloaded = FrequencyAnalyzer()
    reloaded.load(save_path)
    assert reloaded.get_frequency("தமிழக") == 1
    assert reloaded.get_bigram_frequency("தமிழக", "முதலமைச்சர்") == 1


def test_saved_file_is_valid_json(tmp_path):
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழ் மொழி"])
    save_path = tmp_path / "freq.json"
    analyzer.save(save_path)
    with save_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert "word_freq" in data
    assert "bigram_freq" in data


def test_ignores_non_tamil_tokens_in_counts():
    analyzer = FrequencyAnalyzer()
    analyzer.build_from_texts(["தமிழ் News Update மொழி"])
    assert analyzer.get_frequency("News") == 0
    assert analyzer.get_frequency("தமிழ்") == 1
