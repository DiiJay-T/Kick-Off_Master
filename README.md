# KICK-OFF

**A football substitution decision-support research prototype**

KICK-OFF investigates a practical question at the intersection of football, data science and decision-making:

> Can match data help a manager evaluate substitution options as the game situation changes?

The project turns public football match data into a reproducible analysis pipeline and an interactive Streamlit application. A user can inspect a match state, compare two incoming players, review available player information and see a baseline estimate of what happened in the minutes after comparable substitutions.

KICK-OFF is an independent research prototype. It is not a validated player-ranking system or an automated coaching recommendation engine.

## What the project does

- Processes public Wyscout match and event data.
- Validates match records and constructs substitution-level analysis tables.
- Reconstructs a provisional match state around each substitution.
- Trains an interpretable logistic-regression baseline using match-context features.
- Provides an interactive dashboard for exploring match situations and two candidate players.
- Uses stable Wyscout player IDs for identity matching and keeps source records separate from display-name cleanup.
- Presents available FIFA 18 profile data and curated player/coach references as contextual information, not as measured current performance.

## How the current model works

The baseline predicts one of three observed outcomes over the 15 minutes following a recorded substitution:

- **Positive:** the substituted team’s goal difference improves.
- **Neutral:** the goal difference does not change.
- **Negative:** the goal difference worsens.

The current feature set contains:
- Match minute.
- Team score at substitution.
- Opponent score at substitution.
- Score difference.
- Home/away status.
- Match score state.

The model is a logistic-regression pipeline with numerical scaling and one-hot encoding. The evaluation split groups rows by match ID so substitutions from the same match are not distributed across both training and test sets.

### An important interpretation boundary

Candidate-player identity, attributes, fitness and proposed role are **not** inputs to this baseline. Consequently, the probability output describes the match context; it is identical for both candidate options and cannot determine which player is better.

The project also uses observational data. A goal or other outcome after a substitution does not establish that the substitution caused it. Outcome labels are provisional because event-based goal reconstruction has known edge cases. These constraints are part of the research question, not evidence that the model has solved the decision problem.

## Data

The project uses the public Wyscout soccer match event dataset:

- Pappalardo, L. and Massucco, E. (2019), *Soccer match event dataset*, Scientific Data.
- [Figshare dataset collection](https://doi.org/10.6084/m9.figshare.c.4415000)
- [Dataset paper](https://doi.org/10.1038/s41597-019-0247-7)
- [Dataset licence: CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

FIFA 18 player-card data is used as a historical contextual reference where a conservative identity match is available. It is not treated as real-world event performance.

## Run locally

Use Python 3.11 or newer. From the project root:

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the data preparation and training steps:

```bash
python -m scripts.download_wyscout
python -m src.data.validate_matches --data-dir data/raw/matches
python -m src.data.build_substitutions
python -m src.data.build_match_state
python -m src.models.train_baseline
```

Launch the application:

```bash
streamlit run app/app.py
```

Run the automated tests:

```bash
python -m pytest -q
```

Raw data, processed tables and trained model artifacts are generated locally and are not committed to the repository. Follow any instructions in the data directory before running the pipeline.

## Project structure

| Path | Purpose |
|---|---|
| `app/` | Streamlit application |
| `src/data/` | Data loading, validation and feature-table construction |
| `src/models/` | Model training and prediction |
| `scripts/` | Dataset download and profile-building utilities |
| `data/` | Data instructions, references and locally generated datasets |
| `docs/` | Research and architecture notes |
| `tests/` | Automated tests |
| `reports/` | Locally generated evaluation reports |

## Research limitations and next steps

The current version establishes a data and modelling foundation. Further work would need to:

1. Validate event-derived outcome labels against official match scores, including own goals and set-piece edge cases.
2. Build player features from event histories and observed deployment, with sample counts and uncertainty.
3. Derive team tactical profiles from repeated match observations rather than reputation or isolated examples.
4. Train and evaluate a candidate-sensitive model using only information available at the proposed substitution time.
5. Evaluate calibration and performance on chronological, match-aware holdouts.
6. Test whether the model adds decision value beyond a simple match-context baseline.

Any future player comparison should distinguish measured evidence, historical reference data and unverified hypotheses.

## Authorship and use of external resources

KICK-OFF is an independent project. Dataset providers and external data sources are credited above. The repository's code, data transformations, modelling choices and interface should be described according to the work actually completed by the project author. External datasets and reference material are not original data collection.

---

**KICK-OFF · Football analytics · Decision science · Machine learning**
