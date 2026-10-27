"""Extract match-level Wyscout coach IDs and enrich appearances with team names.

Coach IDs are source identifiers; this module does not infer manager names.
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
    "coach_id", "match_appearances", "team_ids", "team_names", "competitions",
    "first_match_date", "last_match_date",
]


def _as_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def load_team_names(teams_file: str | Path) -> dict[int, str]:
    """Load Wyscout team IDs and their display names."""
    path = Path(teams_file)
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    teams = payload.get("teams", []) if isinstance(payload, dict) else payload
    if not isinstance(teams, list):
        raise ValueError(f"Expected a list of teams in {path}")

    names = {}
    for team in teams:
        if not isinstance(team, dict):
            continue
        team_id = _as_int(team.get("wyId"))
        name = team.get("name") or team.get("officialName")
        if team_id is not None and name:
            names[team_id] = str(name)
    return names


def extract_coach_appearances(
    matches_dir: str | Path,
    team_names: dict[int, str] | None = None,
) -> pd.DataFrame:
    """Return one row per coach/team/match, with names where metadata exists."""
    root = Path(matches_dir)
    files = sorted(root.glob("matches_*.json"))
    if not files:
        raise FileNotFoundError(f"No matches_*.json files found in {root}")

    team_names = team_names or {}
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
                opponent = by_side.get("away" if side == "home" else "home", {})
                coach_id = _as_int(team.get("coachId"))
                team_id = _as_int(team.get("teamId"))
                opponent_id = _as_int(opponent.get("teamId"))
                if coach_id is None or team_id is None or match_id is None:
                    continue

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
                    "team_name": team_names.get(team_id),
                    "opponent_name": team_names.get(opponent_id),
                    "team_score": _as_int(team.get("score")),
                    "opponent_score": _as_int(opponent.get("score")),
                })

    return pd.DataFrame(rows, columns=APPEARANCE_COLUMNS)


def summarize_coaches(appearances: pd.DataFrame) -> pd.DataFrame:
    """Aggregate observed coach IDs without assuming continuous employment."""
    if appearances.empty:
        return pd.DataFrame(columns=REGISTRY_COLUMNS)

    data = appearances.copy()
    data["parsed_date"] = pd.to_datetime(
        data["match_date"], errors="coerce", utc=True
    )
    rows = []

    for coach_id, group in data.groupby("coach_id", sort=True):
        dates = group["parsed_date"].dropna()
        names = sorted(group["team_name"].dropna().astype(str).unique())
        rows.append({
            "coach_id": int(coach_id),
            "match_appearances": int(group["match_id"].nunique()),
            "team_ids": ";".join(
                map(str, sorted(group["team_id"].dropna().unique()))
            ),
            "team_names": ";".join(names),
            "competitions": ";".join(
                sorted(group["competition"].dropna().unique())
            ),
            "first_match_date": dates.min().isoformat() if not dates.empty else None,
            "last_match_date": dates.max().isoformat() if not dates.empty else None,
        })

    return pd.DataFrame(rows, columns=REGISTRY_COLUMNS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matches-dir", type=Path, default=Path("data/raw/matches"))
    parser.add_argument("--teams-file", type=Path, default=Path("data/raw/teams.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    team_names = load_team_names(args.teams_file)
    appearances = extract_coach_appearances(args.matches_dir, team_names)
    registry = summarize_coaches(appearances)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    appearances.to_csv(args.output_dir / "coach_appearances.csv", index=False)
    registry.to_csv(args.output_dir / "coach_registry.csv", index=False)

    named = appearances["team_name"].notna().sum()
    print(f"Coach appearances: {len(appearances):,}")
    print(f"Unique coach IDs: {len(registry):,}")
    print(f"Appearances with team names: {named:,}/{len(appearances):,}")
    print(f"Saved: {args.output_dir / 'coach_appearances.csv'}")
    print(f"Saved: {args.output_dir / 'coach_registry.csv'}")


if __name__ == "__main__":
    main()
