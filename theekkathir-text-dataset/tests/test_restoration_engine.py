"""Unit tests for text_cleaner.restoration_engine."""

import pytest

from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.frequency_analyzer import FrequencyAnalyzer
from text_cleaner.restoration_engine import RestorationEngine


@pytest.fixture
def dictionary_loader(tmp_path):
    path = tmp_path / "dict.txt"
    path.write_text(
        "தமிழ்\nமொழி\nதமிழக\nமுதலமைச்சர்\nகுறிப்பிடத்தக்க\nபேசினார்\n",
        encoding="utf-8",
    )
    return DictionaryLoader(path=path)


@pytest.fixture
def engine(dictionary_loader):
    return RestorationEngine(dictionary_loader=dictionary_loader)


def test_merges_split_word_present_in_dictionary(engine):
    result = engine.restore("முதலமை ச்சர்")
    assert result == "முதலமைச்சர்"


def test_merges_another_split_word(engine):
    result = engine.restore("குறிப்பி டத்தக்க")
    assert result == "குறிப்பிடத்தக்க"


def test_does_not_merge_two_valid_independent_words(engine):
    result = engine.restore("தமிழ் மொழி")
    assert result == "தமிழ் மொழி"


def test_context_score_boosts_correct_merge(dictionary_loader):
    freq = FrequencyAnalyzer()
    freq.build_from_texts(
        [
            "தமிழக முதலமைச்சர் பேசினார்",
            "தமிழக முதலமைச்சர் அறிவித்தார்",
        ]
    )
    engine = RestorationEngine(dictionary_loader=dictionary_loader, frequency_analyzer=freq)
    result = engine.restore("தமிழக முதலமை ச்சர் பேசினார்")
    assert "முதலமைச்சர்" in result


def test_full_pipeline_clean_article(engine):
    result = engine.clean_article("தமிழ்\xa0மொழி News Update முதலமை  ச்சர்")
    assert result == "தமிழ் மொழி முதலமைச்சர்"


def test_spell_validator_rejects_nonsense_merge(dictionary_loader):
    # Neither fragment nor merge exists in the dictionary or has frequency
    # support, so the engine must not fabricate a new "word".
    engine = RestorationEngine(dictionary_loader=dictionary_loader)
    result = engine.restore("எக்ஸ் ஒய்ஜட்")
    assert result == "எக்ஸ் ஒய்ஜட்"


def test_compute_confidence_returns_decision_object(engine):
    decision = engine.compute_confidence("முதலமை", "ச்சர்")
    assert decision.merged_candidate == "முதலமைச்சர்"
    assert decision.merged is True
    assert 0.0 <= decision.merged_score <= 1.0


def test_stats_are_recorded_after_restore(engine):
    engine.restore("முதலமை ச்சர்")
    assert engine.last_stats.words_restored == 1
    assert engine.last_stats.pairs_considered >= 1


def test_empty_text_returns_empty(engine):
    assert engine.restore("") == ""
    assert engine.clean_article("") == ""


def test_single_word_is_untouched(engine):
    assert engine.restore("தமிழ்") == "தமிழ்"


def test_max_merged_length_guard(dictionary_loader):
    engine = RestorationEngine(dictionary_loader=dictionary_loader)
    long_fragment_a = "அ" * 15
    long_fragment_b = "ஆ" * 15
    result = engine.restore(f"{long_fragment_a} {long_fragment_b}")
    # Merged candidate exceeds MAX_MERGED_WORD_LENGTH, so must stay split.
    assert result == f"{long_fragment_a} {long_fragment_b}"
