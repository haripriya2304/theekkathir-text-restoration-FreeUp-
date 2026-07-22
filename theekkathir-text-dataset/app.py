#!/usr/bin/env python3
"""
app.py
======

A simple point-and-click UI for the Tamil Text Restoration Engine,
built with Streamlit.

Lets you:
    1. Upload a dataset (.csv or .parquet).
    2. Pick which column holds the article text.
    3. Run the full cleaning pipeline (Unicode -> English -> spacing
       -> word restoration -> spell validation).
    4. Preview a before/after sample and the quality report.
    5. Download a ZIP containing the cleaned dataset, the quality
       report, and the run log.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow running `streamlit run app.py` from the repo root without
# installing the package first.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from text_cleaner import config  # noqa: E402
from text_cleaner.dictionary_loader import DictionaryLoader  # noqa: E402
from text_cleaner.frequency_analyzer import FrequencyAnalyzer  # noqa: E402
from text_cleaner.pipeline import process_dataframe  # noqa: E402
from text_cleaner.restoration_engine import RestorationEngine  # noqa: E402

st.set_page_config(page_title="Tamil Text Restoration Engine", page_icon="🧹", layout="wide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Load an uploaded CSV or Parquet file into a DataFrame."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(uploaded_file)
    if suffix == ".parquet":
        return pd.read_parquet(uploaded_file)
    raise ValueError(f"Unsupported file type '{suffix}'. Please upload a .csv or .parquet file.")


def build_output_bytes(df: pd.DataFrame, suffix: str) -> bytes:
    """Serialize *df* back to bytes in its original format."""
    buffer = io.BytesIO()
    if suffix == ".csv":
        df.to_csv(buffer, index=False, encoding="utf-8")
    elif suffix == ".parquet":
        df.to_parquet(buffer, index=False)
    else:
        raise ValueError(f"Unsupported output format '{suffix}'.")
    buffer.seek(0)
    return buffer.read()


def build_result_zip(
    cleaned_bytes: bytes,
    cleaned_filename: str,
    report_json: str,
    log_text: str,
) -> bytes:
    """Package the cleaned dataset, quality report, and log into a ZIP."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(cleaned_filename, cleaned_bytes)
        zf.writestr("quality_report.json", report_json)
        zf.writestr("cleaning.log", log_text)
    buffer.seek(0)
    return buffer.read()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🧹 Tamil Text Restoration Engine")
st.caption(
    "Upload a Theekkathir-style dataset, clean Unicode noise, strip stray English "
    "tokens, and restore split Tamil words — then download the cleaned dataset as a ZIP."
)

with st.sidebar:
    st.header("Settings")
    dictionary_choice = st.radio(
        "Tamil dictionary",
        options=["Use built-in dictionary", "Upload custom dictionary (.txt)"],
        index=0,
    )
    custom_dictionary_file = None
    if dictionary_choice == "Upload custom dictionary (.txt)":
        custom_dictionary_file = st.file_uploader(
            "Dictionary file (one Tamil word per line)", type=["txt"]
        )
    st.divider()
    st.markdown(
        "**Pipeline stages:**\n"
        "1. Unicode cleaning\n"
        "2. English noise removal\n"
        "3. Whitespace normalization\n"
        "4. Tamil word restoration\n"
        "5. Spell validation"
    )

uploaded_file = st.file_uploader("Upload dataset", type=["csv", "parquet"])

if uploaded_file is None:
    st.info("Upload a .csv or .parquet file to get started.")
    st.stop()

try:
    df = read_uploaded_file(uploaded_file)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not read the uploaded file: {exc}")
    st.stop()

st.success(f"Loaded **{len(df):,}** rows and **{len(df.columns)}** columns.")
st.dataframe(df.head(5), use_container_width=True)

default_column = (
    config.PipelineConfig.text_column if config.PipelineConfig.text_column in df.columns
    else df.columns[0]
)
text_column = st.selectbox(
    "Which column contains the article text?",
    options=list(df.columns),
    index=list(df.columns).index(default_column),
)

run_clicked = st.button("🚀 Clean & Restore Dataset", type="primary")

if run_clicked:
    # --- Build the dictionary loader ------------------------------------
    if custom_dictionary_file is not None:
        custom_path = Path("/tmp") / "uploaded_tamil_dictionary.txt"
        custom_path.write_bytes(custom_dictionary_file.getvalue())
        dictionary_loader = DictionaryLoader(path=custom_path)
    else:
        dictionary_loader = DictionaryLoader(path=config.DEFAULT_DICTIONARY_PATH)

    frequency_analyzer = FrequencyAnalyzer()
    engine = RestorationEngine(
        dictionary_loader=dictionary_loader, frequency_analyzer=frequency_analyzer
    )

    progress_bar = st.progress(0, text="Building frequency statistics...")

    def _on_progress(i: int, total: int) -> None:
        pct = int((i / total) * 100) if total else 100
        progress_bar.progress(pct, text=f"Cleaning article {i:,} / {total:,}")

    with st.spinner("Cleaning dataset..."):
        try:
            cleaned_df, report = process_dataframe(
                df, text_column, engine=engine, progress_callback=_on_progress
            )
        except KeyError as exc:
            st.error(str(exc))
            st.stop()

    progress_bar.progress(100, text="Done!")
    st.success("✅ Cleaning complete!")

    # --- Metrics -----------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Articles processed", f"{report.total_articles:,}")
    m2.metric("Words restored", f"{report.words_restored:,}")
    m3.metric("Articles changed", f"{report.cleaning_percentage:.1f}%")
    m4.metric("Avg. merge confidence", f"{report.average_confidence:.2f}")

    m5, m6, m7 = st.columns(3)
    m5.metric("Unicode noise removed", f"{report.unicode_removed:,}")
    m6.metric("English tokens removed", f"{report.english_words_removed:,}")
    m7.metric("Rejected merge candidates", f"{report.unknown_words:,}")

    # --- Before / after preview --------------------------------------------
    st.subheader("Before / After Preview")
    preview_df = pd.DataFrame(
        {
            "original": df[text_column].fillna("").astype(str).head(10),
            "cleaned": cleaned_df[text_column].fillna("").astype(str).head(10),
        }
    )
    changed_only = preview_df[preview_df["original"] != preview_df["cleaned"]]
    st.dataframe(
        changed_only if not changed_only.empty else preview_df,
        use_container_width=True,
    )

    # --- Build downloadable ZIP ---------------------------------------------
    suffix = Path(uploaded_file.name).suffix.lower()
    cleaned_bytes = build_output_bytes(cleaned_df, suffix)
    cleaned_filename = f"cleaned_{Path(uploaded_file.name).stem}{suffix}"

    import json as _json

    log_path = config.DEFAULT_LOG_FILE
    log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""

    zip_bytes = build_result_zip(
        cleaned_bytes=cleaned_bytes,
        cleaned_filename=cleaned_filename,
        report_json=_json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        log_text=log_text,
    )

    st.download_button(
        label="⬇️ Download cleaned dataset (.zip)",
        data=zip_bytes,
        file_name=f"cleaned_{Path(uploaded_file.name).stem}.zip",
        mime="application/zip",
        type="primary",
    )
