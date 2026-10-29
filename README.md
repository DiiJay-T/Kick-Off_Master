# KICK-OFF

**Football intelligence · Decision science · Machine learning**

KICK-OFF is a football analytics research prototype exploring:

> Can match data help a manager compare two possible substitutions in a changing game situation?

The Streamlit MVP lets a user set a match situation, select two incoming players, inspect their Wyscout names and listed positions, and view an estimate for the match context.

## Current MVP

- Wyscout 2017/18 match and event data for the English, Spanish, Italian, German and French first divisions, plus the 2018 FIFA World Cup and UEFA Euro 2016.
- Validated match metadata and a processed substitution table.
- A logistic-regression baseline trained on match-state features.
- A Streamlit comparison screen with player identity and source-listed position.
- Explicit reporting of model limitations.

## Model scope

The current baseline uses match minute, team score, opponent score, score difference, home/away side and score state. Its target is the observed goal-difference outcome over the 15 minutes after a substitution.

**Candidate-player identity and attributes are not model inputs.** Both selected players therefore receive the same match-context probabilities. The model cannot currently rank the candidates or claim that either is the better substitution. The displayed position is source metadata, not a calculated role-fit score.

## Limitations and interpretation

- The dataset is observational. An outcome occurring after a substitution does not prove the substitution caused it.
- Outcome labels are preliminary; event-based goal reconstruction has known edge cases requiring further validation.
- The current model is a baseline, not a deployment-ready recommendation system.
- Player composure is not directly measured. Future analysis must use carefully defined performance-under-pressure proxies, not psychological claims.
- Coach IDs are available in match records, but names should only be shown when independently verified.

## Run locally

Use Python 3.11 or newer. From the project root:

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
pip install -r requirements.txt
python -m scripts.download_wyscout
python -m src.data.validate_matches --data-dir data/raw/matches
python -m src.data.build_substitutions
python -m src.data.build_match_state
python -m src.models.train_baseline
streamlit run app/app.py
```

Run automated tests with:

```bash
python -m pytest -q
```

Raw data, processed tables and model artifacts are generated locally and excluded from Git.

## Project structure

- `data/` — source attribution and data instructions.
- `src/data/` — data loading, validation and table construction.
- `src/models/` — baseline training and prediction.
- `app/` — Streamlit dashboard.
- `docs/INTELLIGENCE_ARCHITECTURE.md` — longer-term intelligence design.
- `tests/` — automated tests.

## Dataset and attribution

Luca Pappalardo and Emanuele Massucco (2019), *Soccer match event dataset*, Scientific Data.

- [Figshare collection](https://doi.org/10.6084/m9.figshare.c.4415000)
- [Research paper](https://doi.org/10.1038/s41597-019-0247-7)
- [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)

---

**KICK-OFF — Football intelligence · Decision science · Machine learning**
