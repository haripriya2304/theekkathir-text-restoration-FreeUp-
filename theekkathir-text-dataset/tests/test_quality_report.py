"""Unit tests for text_cleaner.quality_report."""

import json
import time

from text_cleaner.quality_report import QualityReport


def test_records_and_finalizes_stats():
    report = QualityReport()
    report.start()
    report.record_article(
        unicode_removed=2,
        english_removed=1,
        words_restored=1,
        unknown_words=0,
        average_confidence=0.9,
        changed=True,
    )
    report.record_article(
        unicode_removed=0,
        english_removed=0,
        words_restored=0,
        unknown_words=1,
        average_confidence=0.0,
        changed=False,
    )
    report.finalize()

    assert report.total_articles == 2
    assert report.unicode_removed == 2
    assert report.english_words_removed == 1
    assert report.words_restored == 1
    assert report.unknown_words == 1
    assert report.cleaning_percentage == 50.0
    assert report.average_confidence == 0.9


def test_finalize_with_no_articles_does_not_divide_by_zero():
    report = QualityReport()
    report.start()
    report.finalize()
    assert report.cleaning_percentage == 0.0
    assert report.average_confidence == 0.0


def test_execution_time_is_measured():
    report = QualityReport()
    report.start()
    time.sleep(0.01)
    report.finalize()
    assert report.execution_time_seconds > 0


def test_save_writes_valid_json(tmp_path):
    report = QualityReport()
    report.start()
    report.record_article(
        unicode_removed=1,
        english_removed=0,
        words_restored=1,
        unknown_words=0,
        average_confidence=0.8,
        changed=True,
    )
    report.finalize()

    out_path = tmp_path / "quality_report.json"
    report.save(out_path)

    assert out_path.exists()
    with out_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["total_articles"] == 1
    assert "_confidence_sum" not in data  # private fields must not leak
