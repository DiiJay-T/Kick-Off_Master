# KICK-OFF

**Football intelligence · Decision science · Machine learning**

KICK-OFF is a football analytics project exploring one focused question:

> Can match data help a manager compare two possible substitutions in a changing game situation?

The goal is to build a decision-support prototype that compares two replacement options under the same match conditions. It will estimate likely short-term outcomes, describe role fit and trade-offs, and explain which option the model favours.

## Research approach

1. **Data** — prepare real, documented football match data.
2. **Features** — represent match state, substitution timing and available player information.
3. **Modelling** — establish an interpretable baseline before testing more complex models.
4. **Evaluation** — use match-aware holdout data, suitable classification metrics and probability-calibration checks.
5. **Application** — present comparisons in a focused interactive dashboard.

## Important research limitation

Historical match data is observational. A model trained on it can identify patterns associated with substitutions and subsequent match outcomes; it cannot, by itself, prove that a substitution caused an outcome. KICK-OFF will present predictions as estimates, not causal claims or guarantees.

## Project status

**Stage 1 — Project foundation.** Repository structure and data-loading pipeline are being established. Model outputs will not be presented until the data and evaluation pipeline have been validated.

## Repository layout

- `data/` — local datasets and instructions; raw data is not committed.
- `src/data/` — data loading and validation.
- `src/features/` — feature construction.
- `src/models/` — model training.
- `src/evaluation/` — evaluation utilities.
- `app/` — interactive application.
- `tests/` — automated checks.

## Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Dataset acquisition instructions will be documented in `data/README.md` before any analysis is run.
