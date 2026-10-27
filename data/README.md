# Data

Raw and processed datasets are stored locally and excluded from Git.

## Source

KICK-OFF uses the public **Soccer match event dataset** by Luca Pappalardo and Emanuele Massucco (2019), published on Figshare.

- Collection: https://doi.org/10.6084/m9.figshare.c.4415000
- Dataset paper: https://doi.org/10.1038/s41597-019-0247-7
- License: Creative Commons Attribution 4.0 International (CC BY 4.0). Retain attribution and check the license terms before redistributing any dataset files.

The collection covers the 2017/18 seasons of the English, Spanish, Italian, German and French first divisions, plus the 2018 FIFA World Cup and UEFA Euro 2016.

## Download

From the repository root, run:

```bash
python -m scripts.download_wyscout
```

The downloader stores the original archives and JSON files in `data/raw/`, then extracts the match and event archives into `data/raw/matches/` and `data/raw/events/`.

## Validate match metadata

```bash
python -m src.data.validate_matches --data-dir data/raw/matches
```

## Build the substitution table

```bash
python -m src.data.build_substitutions
```

This creates `data/processed/substitutions.csv`, with one row per valid substitution. The final-score columns are the recorded full-time score, not the score at substitution time.

## Reconstruct substitution match state

```bash
python -m src.data.build_match_state
```

This creates `data/processed/substitution_match_state.csv`. It joins substitutions to match and event data and derives:

- Home and away score at the substitution minute.
- The substituting team's score state (leading, level, or trailing).
- Goals for and against during the following 15 minutes.
- A descriptive outcome label (positive, neutral, or negative), based on the goal difference in that window.

The current implementation uses Wyscout's goal tag (101) on Shot events. It does not yet classify own goals; own-goal handling must be validated against the source encoding before being included. Event timestamps reset at half-time, so second-half event seconds are offset by 45 minutes. Substitution times are recorded as whole minutes, meaning score timing is approximate at minute-level precision.

**Research limitation:** the next-15-minute label is an observed match outcome after a substitution, not evidence that the substitution caused that outcome. It is a preliminary target for analysis and must be interpreted with match context and model validation.

The processed CSV is generated locally; raw and processed data should not be committed to the public repository.

## Local layout

- `raw/` — original downloaded archives and extracted files.
- `processed/` — derived tables created by the project.
