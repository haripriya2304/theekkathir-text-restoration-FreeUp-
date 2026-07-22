"""Unit tests for main.py (the CLI entry point).

These tests exercise the CLI end-to-end using small Parquet fixtures.
They are skipped automatically if no Parquet engine (pyarrow /
fastparquet) is installed, since Parquet I/O is an external dependency
declared in requirements.txt rather than part of this package itself.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip(
    "pyarrow", reason="pyarrow (see requirements.txt) is required for Parquet I/O tests"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import main as cli  # noqa: E402


@pytest.fixture
def sample_input_parquet(tmp_path):
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "content": [
                "தமிழ்\xa0மொழி News Update",
                "முதலமை  ச்சர் அறிவித்தார்",
            ],
        }
    )
    path = tmp_path / "input.parquet"
    df.to_parquet(path, index=False)
    return path


def test_cli_cleans_and_writes_output(tmp_path, sample_input_parquet):
    output_path = tmp_path / "output.parquet"
    args = cli.parse_args(
        [str(sample_input_parquet), str(output_path), "--report",
         "--report-path", str(tmp_path / "quality_report.json")]
    )
    exit_code = cli.run(args)

    assert exit_code == 0
    assert output_path.exists()

    result_df = pd.read_parquet(output_path)
    assert result_df.loc[0, "content"] == "தமிழ் மொழி"
    assert (tmp_path / "quality_report.json").exists()


def test_cli_fails_gracefully_on_missing_input(tmp_path):
    args = cli.parse_args(
        [str(tmp_path / "missing.parquet"), str(tmp_path / "out.parquet")]
    )
    exit_code = cli.run(args)
    assert exit_code == 1


def test_cli_fails_on_missing_column(tmp_path, sample_input_parquet):
    output_path = tmp_path / "output.parquet"
    args = cli.parse_args(
        [str(sample_input_parquet), str(output_path), "--column", "does_not_exist"]
    )
    exit_code = cli.run(args)
    assert exit_code == 1
