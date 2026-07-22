"""Unit tests for text_cleaner.dictionary_loader."""

import pytest

from text_cleaner.dictionary_loader import DictionaryLoader


@pytest.fixture
def sample_dictionary_path(tmp_path):
    path = tmp_path / "sample_dictionary.txt"
    path.write_text(
        "# comment line, should be ignored\n"
        "\n"
        "தமிழ்\n"
        "மொழி\n"
        "முதலமைச்சர்\n",
        encoding="utf-8",
    )
    return path


def test_loads_words_from_file(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    words = loader.load()
    assert "தமிழ்" in words
    assert "மொழி" in words
    assert "முதலமைச்சர்" in words


def test_ignores_comments_and_blank_lines(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    words = loader.load()
    assert "" not in words
    assert "# comment line, should be ignored" not in words


def test_contains_helper(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    assert loader.contains("தமிழ்") is True
    assert loader.contains("இல்லாதசொல்") is False


def test_missing_file_raises(tmp_path):
    loader = DictionaryLoader(path=tmp_path / "does_not_exist.txt")
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_caching_avoids_rereading(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    first = loader.load()
    # Mutate the underlying file; without force_reload the cache should stick.
    sample_dictionary_path.write_text("புதியசொல்\n", encoding="utf-8")
    second = loader.load()
    assert first == second


def test_force_reload_picks_up_changes(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    loader.load()
    sample_dictionary_path.write_text("புதியசொல்\n", encoding="utf-8")
    reloaded = loader.load(force_reload=True)
    assert "புதியசொல்" in reloaded


def test_add_words_extends_dictionary(sample_dictionary_path):
    loader = DictionaryLoader(path=sample_dictionary_path)
    loader.load()
    loader.add_words({"புதியவார்த்தை"})
    assert loader.contains("புதியவார்த்தை") is True
