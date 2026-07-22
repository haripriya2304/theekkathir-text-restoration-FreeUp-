# Tamil Text Restoration Engine

A production-quality text-cleaning module built as an open-source
contribution to the **Theekkathir Tamil News Dataset**, addressing the
issue:

> Clean up unwanted words present in theekkathir-text-dataset.

Instead of blindly replacing characters, this engine **intelligently
restores** corrupted Tamil text — deciding, word by word, whether
fragments should be merged back together using dictionary lookup,
dataset-wide frequency analysis, and contextual (bigram) scoring.

---

## Problem It Solves

OCR / PDF-to-text extraction in the original dataset introduces
several recurring issues:

| Issue                     | Before                          | After                    |
|----------------------------|----------------------------------|---------------------------|
| Non-breaking space         | `தமிழ்\xa0மொழி`                 | `தமிழ் மொழி`              |
| Zero-width / BOM noise      | `தமிழ்\u200bமொழி`               | `தமிழ்மொழி`               |
| Stray English tokens        | `தமிழ் News Update`             | `தமிழ்`                   |
| Irregular whitespace        | `தமிழ்        மொழி`             | `தமிழ் மொழி`              |
| Split Tamil words           | `குறிப்பி டத்தக்க`               | `குறிப்பிடத்தக்க`          |
| Split Tamil words           | `முதலமை ச்சர்`                   | `முதலமைச்சர்`              |

The hardest of these — deciding whether two adjacent Tamil tokens
should be merged — is handled by a scored decision process rather
than a fixed rule list. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for full algorithm details.

---

## 🚀 Step-by-Step: Setup, Run, and Test

```bash
# 1. Unzip / clone the project, then enter it
cd theekkathir-text-dataset

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the automated test suite (should all pass)
pytest tests/ -v

# 5a. Launch the UI (recommended) — opens http://localhost:8501
streamlit run app.py
#     -> Upload sample_data/sample_dataset.csv (or your own .csv/.parquet)
#     -> Pick the text column, click "Clean & Restore Dataset"
#     -> Download the resulting ZIP

# 5b. OR run the CLI directly on a Parquet file
python main.py sample_data/your_dataset.parquet output/cleaned.parquet --report --verbose
```

**Sanity check** the restoration logic without a UI at all:

```bash
python -c "
from src.text_cleaner.restoration_engine import RestorationEngine
engine = RestorationEngine()
print(engine.clean_article('தமிழ்\xa0மொழி முதலமை  ச்சர் News Update'))
"
# Expected output: தமிழ் மொழி முதலமைச்சர்
```

---

## Installation

```bash
git clone https://github.com/<your-username>/theekkathir-text-dataset.git
cd theekkathir-text-dataset
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Quick Start (Python API)

```python
from text_cleaner.restoration_engine import RestorationEngine

engine = RestorationEngine()
print(engine.clean_article("தமிழ்\xa0மொழி முதலமை  ச்சர் News Update"))
# -> "தமிழ் மொழி முதலமைச்சர்"
```

Each stage is also usable independently:

```python
from text_cleaner.unicode_cleaner import UnicodeCleaner
from text_cleaner.english_cleaner import EnglishCleaner
from text_cleaner.space_normalizer import SpaceNormalizer

text = UnicodeCleaner().clean("தமிழ்\xa0மொழி")
text = EnglishCleaner().clean(text)
text = SpaceNormalizer().normalize(text)
```

---

## 🖥️ UI Usage (Upload a Dataset, Download a Cleaned ZIP)

The easiest way to use this project is the built-in Streamlit UI —
no command-line arguments needed.

```bash
streamlit run app.py
```

This opens `http://localhost:8501` in your browser. From there:

1. **Upload** a `.csv` or `.parquet` file (a ready-made example is at
   `sample_data/sample_dataset.csv`).
2. **Select the text column** to clean (e.g. `content`).
3. Optionally upload a custom Tamil dictionary `.txt` in the sidebar.
4. Click **"🚀 Clean & Restore Dataset"**.
5. Review the live stats (words restored, articles changed, average
   confidence) and the before/after preview table.
6. Click **"⬇️ Download cleaned dataset (.zip)"** — the ZIP contains:
   - `cleaned_<your-file>` (same format as the upload)
   - `quality_report.json`
   - `cleaning.log`

---

## CLI Usage

```bash
python main.py input.parquet output.parquet
python main.py input.parquet output.parquet --report
python main.py input.parquet output.parquet --report --verbose
python main.py input.parquet output.parquet --column content
python main.py input.parquet output.parquet --dictionary resources/tamil_dictionary.txt
```

| Flag              | Description                                                       |
|--------------------|---------------------------------------------------------------------|
| `--column`         | Name of the text column to clean (default: `content`)              |
| `--dictionary`     | Path to a custom Tamil dictionary word list                        |
| `--report`         | Write `output/quality_report.json` summarising the run             |
| `--report-path`    | Custom path for the quality report                                 |
| `--verbose`        | Enable DEBUG-level console logging                                 |

Every run also writes `logs/cleaning.log` with full execution details,
warnings, and statistics.

---

## Architecture

```
Raw Article
    │
    ▼
UnicodeCleaner  →  EnglishCleaner  →  SpaceNormalizer  →  RestorationEngine  →  SpaceNormalizer
                                                                │
                                                    DictionaryLoader · FrequencyAnalyzer · SpellValidator
    │
    ▼
Clean Article
```

Full details, including the exact confidence-scoring formula, live in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Project Structure

```
src/text_cleaner/
    __init__.py
    config.py              # all tunable constants, weights, paths
    utils.py                # logging setup, Tamil/English token helpers
    unicode_cleaner.py      # Module 1: Unicode noise removal
    english_cleaner.py      # Module 2: English token removal
    space_normalizer.py     # Module 3: whitespace normalization
    restoration_engine.py   # Module 4: core word-restoration algorithm
    spell_validator.py      # Module 5: final validation gate
    dictionary_loader.py    # Tamil dictionary loading
    frequency_analyzer.py   # dataset-wide unigram/bigram frequency stats
    quality_report.py       # Module 6: dataset-wide quality report
    pipeline.py              # shared process_dataframe() used by CLI + UI

tests/            # pytest unit tests for every module (incl. pipeline & CLI)
docs/             # architecture documentation
resources/        # tamil_dictionary.txt
sample_data/      # example dataset + before/after CSV for quick testing
output/           # generated quality_report.json (git-ignored contents)
logs/             # generated cleaning.log (git-ignored contents)
main.py           # CLI entry point
app.py            # Streamlit UI: upload a dataset, download a cleaned ZIP
requirements.txt
```

---

## Example (from `sample_data/before_after_examples.csv`)

| Original                                                       | Cleaned                                            |
|-------------------------------------------------------------------|------------------------------------------------------|
| `தமிழக முதலமை  ச்சர் புதிய திட்டத்தை News Update அறிவித்தார்.` | `தமிழக முதலமைச்சர் புதிய திட்டத்தை அறிவித்தார்.`      |
| `இது ஒரு குறிப்பி டத்தக்க நிகழ்வு என அரசு தெரிவித்துள்ளது.`     | `இது ஒரு குறிப்பிடத்தக்க நிகழ்வு என அரசு தெரிவித்துள்ளது.` |
| `சென்னையில்        மழை பெய்தது LIVE Breaking.`                    | `சென்னையில் மழை பெய்தது.`                            |

A sample `output/quality_report.json` generated from this data is
included in the repository for reference.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover Unicode cleaning, English-token removal, whitespace
normalization, dictionary loading, frequency analysis, spell
validation, the restoration algorithm's merge/split decisions, the
quality report, and the CLI (Parquet-dependent CLI tests are
auto-skipped if `pyarrow` is not installed).

---

## Extending the Dictionary

`resources/tamil_dictionary.txt` is a plain newline-delimited word
list (UTF-8, `#` for comments). Contributors are encouraged to grow
this list — the restoration engine's dictionary score improves
directly with dictionary coverage. Words can also be added
programmatically:

```python
from text_cleaner.dictionary_loader import DictionaryLoader

loader = DictionaryLoader()
loader.add_words({"புதியசொல்"})
```

---

## Contribution Guide

This module is intended to be merged into the existing dataset
generation pipeline, right before articles are written to the final
Parquet file:

```
Raw Article → UnicodeCleaner → EnglishCleaner → SpaceNormalizer
            → RestorationEngine → SpellValidator → Save Clean Dataset
```

To contribute:

1. Fork the repository and create a feature branch.
2. Add/modify a module under `src/text_cleaner/`, following the
   existing docstring + type-hint + logging conventions.
3. Add corresponding tests under `tests/`.
4. Run `pytest tests/ -v` and ensure everything passes.
5. Update `docs/ARCHITECTURE.md` if you change the scoring algorithm
   or pipeline order.
6. Open a pull request describing the problem solved, the cleaning
   strategy used, test results, and sample before/after output.

### Git Workflow

```bash
git checkout -b feature/tamil-text-restoration
# ... make changes ...
git add .
git commit -m "Add Tamil Text Restoration Engine for dataset cleaning"
git push origin feature/tamil-text-restoration
# Open a Pull Request against the original repository's main branch.
```

---

## License

This contribution follows the license of the parent
`theekkathir-text-dataset` repository.
