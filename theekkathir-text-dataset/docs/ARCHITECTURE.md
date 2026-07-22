# Architecture

## Overview

The Tamil Text Restoration Engine is a linear pipeline of small,
single-responsibility modules under `src/text_cleaner/`. Each stage
takes a string in and returns a string out, so stages can be tested,
reordered, or swapped independently.

```
Raw Article
    │
    ▼
UnicodeCleaner        removes \xa0, zero-width chars, BOM; NFC normalize
    │
    ▼
EnglishCleaner         strips isolated English noise tokens (News, LIVE, ...)
    │
    ▼
SpaceNormalizer         collapses whitespace runs, trims ends
    │
    ▼
RestorationEngine       merges incorrectly split Tamil word pairs
    │  (uses DictionaryLoader + FrequencyAnalyzer + SpellValidator)
    ▼
SpaceNormalizer          final whitespace pass (merges can shift spacing)
    │
    ▼
Clean Article
```

`RestorationEngine.clean_article()` runs the entire chain above. Each
stage is also independently usable for unit testing or partial reuse.

## The Restoration Algorithm

For every pair of **adjacent Tamil-only tokens** `(left, right)` in a
whitespace-tokenized sentence, the engine:

1. Forms a merge candidate: `merged = left + right`.
2. Computes a **merged score** as a weighted sum of three signals:
   - **Dictionary score** — 1.0 if `merged` is a known word, else 0.0.
   - **Frequency score** — compares how often `merged` appears in the
     dataset versus how often `left`/`right` appear as separate
     tokens (Laplace-smoothed log-ratio, squashed through a sigmoid
     into `[0, 1]`).
   - **Context score** — bigram evidence: how often `merged` appears
     next to its actual neighbouring words in the dataset (captures
     phrases such as `தமிழக முதலமைச்சர்`).
3. Computes a **split score** — mostly driven by whether *both*
   fragments are already independently valid dictionary words (strong
   evidence they should **not** be merged).
4. Merges only if `merged_score - split_score` exceeds a configurable
   margin (`MERGE_DECISION_MARGIN`, default `0.05`), **and** the
   resulting word passes `SpellValidator.validate()`.

Weights (`dictionary=0.5, frequency=0.3, context=0.2` by default) are
defined once in `config.ScoringWeights` and can be tuned per-dataset
without touching engine code.

## Why Frequency + Context, Not Dictionary Alone?

A dictionary alone cannot cover every valid Tamil word (proper nouns,
inflected forms, compound words, neologisms). The frequency and
context signals let the engine still make a confident merge decision
for words that are common in the dataset but absent from the static
dictionary — while the `SpellValidator` acts as a final gate so the
engine never *invents* a word purely on frequency grounds without
some corroborating evidence.

## Module Responsibilities

| Module                  | Responsibility                                                        |
|--------------------------|-------------------------------------------------------------------------|
| `unicode_cleaner.py`    | Strip Unicode noise, NFC normalize                                     |
| `english_cleaner.py`    | Remove isolated English noise tokens                                   |
| `space_normalizer.py`   | Collapse/trim whitespace                                               |
| `dictionary_loader.py`  | Load and cache the Tamil word dictionary                               |
| `frequency_analyzer.py` | Build unigram/bigram frequency statistics from the dataset             |
| `spell_validator.py`    | Accept/reject a restored word before it replaces the original text     |
| `restoration_engine.py` | Core merge-decision algorithm + full pipeline orchestration            |
| `quality_report.py`     | Aggregate per-article stats into a dataset-wide JSON report            |
| `config.py`             | All tunable constants, weights, and paths in one place                 |
| `utils.py`               | Shared logging setup and Tamil/English token-classification helpers   |

## Data Flow in `main.py`

1. Read the input Parquet file into a pandas DataFrame.
2. Build a `FrequencyAnalyzer` over the entire text column so context
   and frequency scores are informed by the whole dataset, not just
   one article at a time.
3. Run `RestorationEngine.clean_article()` over every row.
4. Accumulate per-article stats into a `QualityReport`.
5. Write the cleaned DataFrame back out as Parquet.
6. Optionally write `output/quality_report.json`.

## Extensibility

- **Bigger dictionary**: replace/extend `resources/tamil_dictionary.txt`
  (one word per line) or call `DictionaryLoader.add_words()`
  programmatically — no code changes required.
- **Different scoring weights**: pass a custom `config.ScoringWeights`
  into `RestorationEngine`.
- **Persisted frequency stats**: `FrequencyAnalyzer.save()` /
  `.load()` let you reuse frequency statistics across runs instead of
  rebuilding them from scratch each time.
