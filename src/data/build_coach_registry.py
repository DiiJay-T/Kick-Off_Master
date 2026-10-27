"""Extract match-level Wyscout coach IDs and summarize their observed tenures.

Coach IDs are preserved as source identifiers. This module does not infer names.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


APPEARANCE_COLUMNS = [
    "coach_id", "team_id", "team_side", "match_id", "match_date",
    "competition", "team_name", "opponent_name", "team_score", "opponent_score",
]
REGISTRY_COLUMNS = [
    "coach_id", "match_appearances", "team_ids", "competitions",
    "first_match_date", "last_match_date",
]


def _as_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_coach_appearances(matches_dir: str | Path) -> pd.DataFrame:
    """Return one row per coach/team/match from matches_*.json."""
    root = Path(matches_dir)
    files = sorted(root.glob("matches_*.json"))
    if not files:
        raise FileNotFoundError(f"No matches_*.json files found in {root}")

    rows = []
    seen = set()
    for path in files:
        competition = path.stem.removeprefix("matches_")
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        matches = payload.get("matches", []) if isinstance(payload, dict) else payload
        if not isinstance(matches, list):
            continue
        for match in matches:
            if not isinstance(match, dict):
                continue
            match_id = _as_int(match.get("wyId"))
            teams = [
                value for value in (match.get("teamsData") or {}).values()
                if isinstance(value, dict)
            ]
            by_side = {team.get("side"): team for team in teams}
            for side in ("home", "away"):
                team = by_side.get(side, {})
                coach_id = _as_int(team.get("coachId"))
                team_id = _as_int(team.get("teamId"))
                if coach_id is None or team_id is None or match_id is None:
                    continue
                opponent = by_side.get("away" if side == "home" else "home", {})
                key = (coach_id, team_id, match_id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "coach_id": coach_id,
                    "team_id": team_id,
                    "team_side": side,
                    "match_id": match_id,
                    "match_date": match.get("dateutc") or match.get("date"),
                    "competition": competition,
                    "team_name": None,
                    "opponent_name": None,
                    "team_score": _as_int(team.get("score")),
                    "opponent_score": _as_int(opponent.get("score")),
                })
    return pd.DataFrame(rows, columns=APPEARANCE_COLUMNS)


def summarize_coaches(appearances: pd.DataFrame) -> pd.DataFrame:
    """Aggregate observed coach IDs without assuming continuous employment."""
    rows = []
    if appearances.empty:
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    data = appearances.copy()
    data["parsed_date"] = pd.to_datetime(data["match_date"], errors="coerce", utc=True)
    for coach_id, group in data.groupby("coach_id", sort=True):
        dates = group["parsed_date"].dropna()
        rows.append({
            "coach_id": int(coach_id),
            "match_appearances": int(group["match_id"].nunique()),
            "team_ids": ";".join(map(str, sorted(group["team_id"].dropna().unique()))),
            "competitions": ";".join(sorted(group["competition"].dropna().unique())),
            "first_match_date": dates.min().isoformat() if not dates.empty else None,
            "last_match_date": dates.max().isoformat() if not dates.empty else None,
        })
    return pd.DataFrame(rows, columns=REGISTRY_COLUMNS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matches-dir", type=Path, default=Path("data/raw/matches"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    appearances = extract_coach_appearances(args.matches_dir)
    registry = summarize_coaches(appearances)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    appearances.to_csv(args.output_dir / "coach_appearances.csv", index=False)
    registry.to_csv(args.output_dir / "coach_registry.csv", index=False)
    print(f"Coach appearances: {len(appearances):,}")
    print(f"Unique coach IDs: {len(registry):,}")
    print(f"Saved: {args.output_dir / 'coach_appearances.csv'}")
    print(f"Saved: {args.output_dir / 'coach_registry.csv'}")


if __name__ == "__main__":
    main()
