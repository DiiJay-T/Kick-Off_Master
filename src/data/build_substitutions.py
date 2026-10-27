"""Build a row-per-substitution CSV from Wyscout match metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.load_matches import load_match_file


SUBSTITUTION_COLUMNS = [
    "match_id",
    "match_label",
    "match_date",
    "match_date_utc",
    "competition",
    "source_file",
    "season_id",
    "gameweek",
    "match_status",
    "duration",
    "team_id",
    "team_side",
    "substitution_number",
    "minute",
    "player_in",
    "player_out",
    "final_home_score",
    "final_away_score",
]


def build_substitution_table(matches_dir: str | Path) -> pd.DataFrame:
    """Return one row per valid substitution across matches_*.json files.

    Score columns contain the recorded final match score, not the score at
    the substitution minute. Malformed substitutions are skipped by the
    shared Wyscout match loader.
    """
    root = Path(matches_dir)
    files = sorted(root.glob("matches_*.json"))
    if not files:
        raise FileNotFoundError(f"No matches_*.json files found in {root}")

    rows: list[dict] = []
    seen_match_ids: set[int] = set()

    for file_path in files:
        matches = load_match_file(file_path)
        competition = file_path.stem.removeprefix("matches_")

        for match in matches.to_dict(orient="records"):
            match_id = match["match_id"]
            if match_id is not None and match_id in seen_match_ids:
                continue
            if match_id is not None:
                seen_match_ids.add(match_id)

            for side in ("home", "away"):
                substitutions = match[f"{side}_substitutions"] or []
                for number, substitution in enumerate(substitutions, start=1):
                    rows.append(
                        {
                            "match_id": match_id,
                            "match_label": match["label"],
                            "match_date": match["date"],
                            "match_date_utc": match["date_utc"],
                            "competition": competition,
                            "source_file": file_path.name,
                            "season_id": match["season_id"],
                            "gameweek": match["gameweek"],
                            "match_status": match["status"],
                            "duration": match["duration"],
                            "team_id": match[f"{side}_team_id"],
                            "team_side": side,
                            "substitution_number": number,
                            "minute": substitution["minute"],
                            "player_in": substitution["player_in"],
                            "player_out": substitution["player_out"],
                            "final_home_score": match["home_score"],
                            "final_away_score": match["away_score"],
                        }
                    )

    return pd.DataFrame(rows, columns=SUBSTITUTION_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a row-per-substitution CSV from Wyscout match metadata."
    )
    parser.add_argument(
        "--matches-dir",
        type=Path,
        default=Path("data/raw/matches"),
        help="Folder containing matches_*.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/substitutions.csv"),
        help="Destination CSV path.",
    )
    args = parser.parse_args()

    table = build_substitution_table(args.matches_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)

    print(f"Matches directory: {args.matches_dir}")
    print(f"Substitution rows: {len(table):,}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
