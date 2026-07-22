"""Unit tests for text_cleaner.pipeline (shared by CLI and the Streamlit UI)."""

import pandas as pd
import pytest

from text_cleaner.dictionary_loader import DictionaryLoader
from text_cleaner.pipeline import process_dataframe
from text_cleaner.restoration_engine import RestorationEngine


@pytest.fixture
def dictionary_loader(tmp_path):
    path = tmp_path / "dict.txt"
    path.write_text("தமிழ்\nமொழி\nமுதலமைச்சர்\n", encoding="utf-8")
    return DictionaryLoader(path=path)


def test_process_dataframe_cleans_text_column(dictionary_loader):
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "content": ["தமிழ்\xa0மொழி News Update", "முதலமை  ச்சர் அறிவித்தார்"],
        }
    )
    engine = RestorationEngine(dictionary_loader=dictionary_loader)
    cleaned_df, report = process_dataframe(df, "content", engine=engine)

    assert cleaned_df.loc[0, "content"] == "தமிழ் மொழி"
    assert cleaned_df.loc[1, "content"] == "முதலமைச்சர் அறிவித்தார்"
    assert report.total_articles == 2
    assert report.words_restored == 1


def test_process_dataframe_does_not_mutate_input(dictionary_loader):
    df = pd.DataFrame({"content": ["தமிழ்\xa0மொழி"]})
    original_value = df.loc[0, "content"]
    engine = RestorationEngine(dictionary_loader=dictionary_loader)
    process_dataframe(df, "content", engine=engine)
    assert df.loc[0, "content"] == original_value


def test_process_dataframe_missing_column_raises(dictionary_loader):
    df = pd.DataFrame({"content": ["தமிழ்"]})
    engine = RestorationEngine(dictionary_loader=dictionary_loader)
    with pytest.raises(KeyError):
        process_dataframe(df, "does_not_exist", engine=engine)


def test_process_dataframe_calls_progress_callback(dictionary_loader):
    df = pd.DataFrame({"content": ["தமிழ்", "மொழி", "முதலமை ச்சர்"]})
    engine = RestorationEngine(dictionary_loader=dictionary_loader)

    calls = []
    process_dataframe(
        df, "content", engine=engine, progress_callback=lambda i, total: calls.append((i, total))
    )

    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_process_dataframe_creates_default_engine_when_none_given():
    df = pd.DataFrame({"content": ["தமிழ் மொழி"]})
    cleaned_df, report = process_dataframe(df, "content")
    assert cleaned_df.loc[0, "content"] == "தமிழ் மொழி"
    assert report.total_articles == 1
