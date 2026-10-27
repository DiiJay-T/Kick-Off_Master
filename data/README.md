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

The downloader stores the original archives and JSON files in `data/raw/`, then extracts the match and event archives into:

- `data/raw/matches/`
- `data/raw/events/`

The players and teams JSON files remain directly in `data/raw/`.

To choose another local destination:

```bash
python -m scripts.download_wyscout --output-dir path/to/wyscout-data
```

The script skips non-empty files that are already present. Delete a damaged or incomplete local download before rerunning it.

## Validate match metadata

After downloading, run:

```bash
python -m src.data.validate_matches --data-dir data/raw/matches
```

To save a separate report:

```bash
python -m src.data.validate_matches --data-dir data/raw/matches --output data/validation_report.json
```

The validator reads source files without modifying them. The optional report is a separate output file.

## Local layout

- `raw/` — original downloaded archives and extracted files.
- `processed/` — derived tables created by the project.

Raw data and local reports should not be committed to the public repository.
