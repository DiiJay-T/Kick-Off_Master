"""Reconstruct match score and short-window outcomes at substitution time.

Wyscout event seconds reset at the start of each half. Substitution minutes are
whole match minutes, so comparisons are approximate to the recorded minute.
Normal goals use tag 101 on Shot or Free Kick events. Own goals use tag 102
and are credited to the team opposing the event's teamId.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

GOAL_TAG_ID = 101
OWN_GOAL_TAG_ID = 102
GOAL_EVENT_NAMES = {"Shot", "Free Kick"}
OUTPUT_COLUMNS = [
    "match_id", "team_id", "team_side", "minute", "player_in", "player_out",
    "home_score_at_substitution", "away_score_at_substitution",
    "team_score_at_substitution", "opponent_score_at_substitution",
    "score_state", "team_goals_next_15", "opponent_goals_next_15",
    "goal_difference_next_15", "outcome_label",
]


def _absolute_seconds(event: dict) -> float | None:
    period = event.get("matchPeriod")
    seconds = event.get("eventSec")
    if period not in {"1H", "2H"} or not isinstance(seconds, (int, float)):
        return None
    return float(seconds) + (2700.0 if period == "2H" else 0.0)


def _goal_team_id(event: dict, home_id: int, away_id: int) -> int | None:
    """Return the team credited with a goal, or None for non-goal events."""
    tags = event.get("tags", [])
    tag_ids = {
        tag.get("id") for tag in tags if isinstance(tag, dict)
    }
    event_team = event.get("teamId")
    if event_team is None:
        return None
    event_team = int(event_team)

    if OWN_GOAL_TAG_ID in tag_ids:
        if event_team == home_id:
            return away_id
        if event_team == away_id:
            return home_id
        return None

    if event.get("eventName") in GOAL_EVENT_NAMES and GOAL_TAG_ID in tag_ids:
        return event_team if event_team in {home_id, away_id} else None

    return None


def build_match_state_table(
    substitutions_path: str | Path,
    matches_dir: str | Path,
    events_dir: str | Path,
    window_minutes: int = 15,
) -> pd.DataFrame:
    """Add score-at-substitution and next-window goal outcomes to each sub."""
    if window_minutes <= 0:
        raise ValueError("window_minutes must be positive")

    substitutions = pd.read_csv(substitutions_path)
    matches_root = Path(matches_dir)
    events_root = Path(events_dir)
    match_files = sorted(matches_root.glob("matches_*.json"))
    event_files = sorted(events_root.glob("events_*.json"))
    if not match_files or not event_files:
        raise FileNotFoundError("Both match and event JSON directories must contain source files")

    team_lookup: dict[int, tuple[int, int]] = {}
    for path in match_files:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload = payload.get("matches", [])
        for match in payload:
            teams = match.get("teamsData", {}).values()
            home = next((x for x in teams if x.get("side") == "home"), {})
            teams = match.get("teamsData", {}).values()
            away = next((x for x in teams if x.get("side") == "away"), {})
            team_lookup[int(match["wyId"])] = (
                int(home["teamId"]), int(away["teamId"])
            )

    goals_by_match: dict[int, list[tuple[float, int]]] = {}
    for path in event_files:
        with path.open(encoding="utf-8") as handle:
            events = json.load(handle)
        for event in events:
            match_id = event.get("matchId")
            if match_id is None or int(match_id) not in team_lookup:
                continue
            home_id, away_id = team_lookup[int(match_id)]
            scoring_team = _goal_team_id(event, home_id, away_id)
            if scoring_team is None:
                continue
            timestamp = _absolute_seconds(event)
            if timestamp is None:
                continue
            goals_by_match.setdefault(int(match_id), []).append(
                (timestamp, scoring_team)
            )

    rows = []
    for sub in substitutions.to_dict(orient="records"):
        match_id = int(sub["match_id"])
        if match_id not in team_lookup:
            continue
        home_id, away_id = team_lookup[match_id]
        sub_team = int(sub["team_id"])
        if sub_team not in {home_id, away_id}:
            continue

        # Wyscout substitution minute is a whole match-minute value.
        sub_time = float(sub["minute"]) * 60.0
        match_goals = sorted(goals_by_match.get(match_id, []))
        home_score = sum(1 for t, team in match_goals if t <= sub_time and team == home_id)
        away_score = sum(1 for t, team in match_goals if t <= sub_time and team == away_id)
        team_score, opponent_score = (
            (home_score, away_score) if sub_team == home_id else (away_score, home_score)
        )
        next_goals = [
            team for t, team in match_goals
            if sub_time < t <= sub_time + window_minutes * 60
        ]
        team_next = sum(team == sub_team for team in next_goals)
        opponent_id = away_id if sub_team == home_id else home_id
        opponent_next = sum(team == opponent_id for team in next_goals)
        difference = team_next - opponent_next
        label = "positive" if difference > 0 else "negative" if difference < 0 else "neutral"

        rows.append({
            "match_id": match_id,
            "team_id": sub_team,
            "team_side": sub["team_side"],
            "minute": int(sub["minute"]),
            "player_in": int(sub["player_in"]),
            "player_out": int(sub["player_out"]),
            "home_score_at_substitution": home_score,
            "away_score_at_substitution": away_score,
            "team_score_at_substitution": team_score,
            "opponent_score_at_substitution": opponent_score,
            "score_state": "leading" if team_score > opponent_score else "trailing" if team_score < opponent_score else "level",
            "team_goals_next_15": team_next,
            "opponent_goals_next_15": opponent_next,
            "goal_difference_next_15": difference,
            "outcome_label": label,
        })

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build substitution match-state and 15-minute outcome features.")
    parser.add_argument("--substitutions", type=Path, default=Path("data/processed/substitutions.csv"))
    parser.add_argument("--matches-dir", type=Path, default=Path("data/raw/matches"))
    parser.add_argument("--events-dir", type=Path, default=Path("data/raw/events"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/substitution_match_state.csv"))
    parser.add_argument("--window-minutes", type=int, default=15)
    args = parser.parse_args()

    table = build_match_state_table(
        args.substitutions, args.matches_dir, args.events_dir, args.window_minutes
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(f"Substitution rows with match state: {len(table):,}")
    print(f"Output: {args.output}")
    if not table.empty:
        print("Outcome labels:")
        print(table["outcome_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
