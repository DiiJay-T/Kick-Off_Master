"""Load and validate Wyscout match metadata JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


MATCH_COLUMNS = [
    "match_id",
    "label",
    "date",
    "date_utc",
    "competition_id",
    "season_id",
    "gameweek",
    "status",
    "duration",
    "winner_id",
    "home_team_id",
    "away_team_id",
    "home_score",
    "away_score",
    "home_substitutions",
    "away_substitutions",
]


def _as_int(value: Any) -> int | None:
    """Convert an ID-like value to int, returning None when it is invalid."""
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _valid_substitutions(formation: Any) -> list[dict[str, Any]]:
    """Return only well-formed substitution records from a formation."""
    if not isinstance(formation, dict):
        return []

    substitutions = formation.get("substitutions")
    if not isinstance(substitutions, list):
        return []

    valid = []
    for item in substitutions:
        if not isinstance(item, dict):
            continue
        minute = _as_int(item.get("minute"))
        player_in = _as_int(item.get("playerIn"))
        player_out = _as_int(item.get("playerOut"))
        if minute is None or player_in is None or player_out is None:
            continue
        valid.append(
            {"minute": minute, "player_in": player_in, "player_out": player_out}
        )
    return valid


def _team_records(teams_data: Any) -> list[dict[str, Any]]:
    """Normalize the two team entries in a Wyscout teamsData object."""
    if not isinstance(teams_data, dict):
        return []

    records = []
    for raw in teams_data.values():
        if not isinstance(raw, dict):
            continue
        records.append(raw)
    return records


def _extract_match(match: dict[str, Any]) -> dict[str, Any]:
    teams = _team_records(match.get("teamsData"))
    home = next((team for team in teams if team.get("side") == "home"), {})
    away = next((team for team in teams if team.get("side") == "away"), {})

    home_formation = home.get("formation")
    away_formation = away.get("formation")

    return {
        "match_id": _as_int(match.get("wyId")),
        "label": match.get("label"),
        "date": match.get("date"),
        "date_utc": match.get("dateutc"),
        "competition_id": _as_int(match.get("competitionId")),
        "season_id": _as_int(match.get("seasonId")),
        "gameweek": _as_int(match.get("gameweek")),
        "status": match.get("status"),
        "duration": match.get("duration"),
        "winner_id": _as_int(match.get("winner")),
        "home_team_id": _as_int(home.get("teamId")),
        "away_team_id": _as_int(away.get("teamId")),
        "home_score": _as_int(home.get("score")),
        "away_score": _as_int(away.get("score")),
        "home_substitutions": _valid_substitutions(home_formation),
        "away_substitutions": _valid_substitutions(away_formation),
    }


def load_match_file(path: str | Path) -> pd.DataFrame:
    """Load one Wyscout matches_*.json file into a normalized DataFrame.

    The loader tolerates malformed or missing substitution entries by skipping
    those entries rather than failing the entire file.
    """
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        matches = payload.get("matches", [])
    elif isinstance(payload, list):
        matches = payload
    else:
        raise ValueError(f"Unsupported JSON structure in {file_path}")

    if not isinstance(matches, list):
        raise ValueError(f"Expected a list of matches in {file_path}")

    rows = [_extract_match(match) for match in matches if isinstance(match, dict)]
    frame = pd.DataFrame(rows, columns=MATCH_COLUMNS)

    if frame["match_id"].notna().any():
        frame = frame.drop_duplicates(subset="match_id", keep="first")

    return frame.reset_index(drop=True)


def load_match_directory(directory: str | Path) -> pd.DataFrame:
    """Load and combine all matches_*.json files in a directory."""
    root = Path(directory)
    files = sorted(root.glob("matches_*.json"))
    if not files:
        raise FileNotFoundError(f"No matches_*.json files found in {root}")

    frames = [load_match_file(file_path) for file_path in files]
    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(subset="match_id", keep="first").reset_index(drop=True)
