"""Unit tests for text_cleaner.spell_validator."""

import pytest

from text_cleaner import config
from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.frequency_analyzer import FrequencyAnalyzer
from text_cleaner.spell_validator import SpellValidator


@pytest.fixture
def dictionary_loader(tmp_path):
    path = tmp_path / "dict.txt"
    path.write_text("தமிழ்\nமொழி\nமுதலமைச்சர்\n", encoding="utf-8")
    return DictionaryLoader(path=path)


def test_accepts_word_in_dictionary(dictionary_loader):
    validator = SpellValidator(dictionary_loader=dictionary_loader)
    assert validator.validate("தமிழ்") is True


def test_rejects_word_not_in_dictionary_without_frequency_fallback(dictionary_loader):
    cfg = config.SpellValidatorConfig(require_dictionary_or_frequency=False)
    validator = SpellValidator(dictionary_loader=dictionary_loader, validator_config=cfg)
    assert validator.validate("இல்லாதசொல்") is False


def test_accepts_unlisted_word_with_sufficient_frequency(dictionary_loader):
    freq = FrequencyAnalyzer()
    # Build up frequency evidence for a word not in the dictionary.
    freq.build_from_texts(["புதியசொல் புதியசொல் புதியசொல் புதியசொல்"])
    cfg = config.SpellValidatorConfig(
        require_dictionary_or_frequency=True, min_frequency_if_unlisted=3
    )
    validator = SpellValidator(
        dictionary_loader=dictionary_loader, frequency_analyzer=freq, validator_config=cfg
    )
    assert validator.validate("புதியசொல்") is True


def test_rejects_unlisted_word_with_insufficient_frequency(dictionary_loader):
    freq = FrequencyAnalyzer()
    freq.build_from_texts(["அரிதானசொல்"])
    cfg = config.SpellValidatorConfig(
        require_dictionary_or_frequency=True, min_frequency_if_unlisted=5
    )
    validator = SpellValidator(
        dictionary_loader=dictionary_loader, frequency_analyzer=freq, validator_config=cfg
    )
    assert validator.validate("அரிதானசொல்") is False


def test_rejects_empty_word(dictionary_loader):
    validator = SpellValidator(dictionary_loader=dictionary_loader)
    assert validator.validate("") is False


def test_rejects_word_starting_with_dependent_vowel_sign(dictionary_loader):
    validator = SpellValidator(dictionary_loader=dictionary_loader)
    # U+0BC7 (Tamil vowel sign E) can never legally start a word.
    assert validator.validate("\u0BC7தமிழ்") is False
