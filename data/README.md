# Data

Raw and processed datasets belong in this directory locally, but are excluded from Git.

## Current source direction

KICK-OFF is beginning with the public Wyscout research data. Before analysis, the project will document the exact source page, dataset version, license/usage terms, and citation required by the provider.

## Local layout

- `raw/` — original downloaded files, unchanged.
- `processed/` — validated tables produced by the pipeline.

Do not manually edit raw source files. Do not commit raw data or redistribute it until its terms have been checked.

## Validate downloaded match files

Place the original `matches_*.json` files in `data/raw/`, then run this command from the repository root:

```bash
python -m src.data.validate_matches --data-dir data/raw
```

The report includes file and match counts, unique and duplicate match IDs, missing required match fields, teams with missing required fields, and valid versus malformed substitution records.

To save a separate JSON report:

```bash
python -m src.data.validate_matches --data-dir data/raw --output data/validation_report.json
```

The validator reads raw files only. It does not edit them. The optional report is a separate output file.
