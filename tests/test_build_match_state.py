import json

import pandas as pd

from src.data.build_match_state import build_match_state_table


def _match():
    return [{
        "wyId": 10,
        "teamsData": {
            "home": {"side": "home", "teamId": 1},
            "away": {"side": "away", "teamId": 2},
        },
    }]


def _write_inputs(tmp_path, event_rows):
    matches = tmp_path / "matches"
    events = tmp_path / "events"
    matches.mkdir()
    events.mkdir()
    (matches / "matches_England.json").write_text(json.dumps(_match()), encoding="utf-8")
    (events / "events_England.json").write_text(json.dumps(event_rows), encoding="utf-8")
    subs = pd.DataFrame([{
        "match_id": 10, "team_id": 1, "team_side": "home", "minute": 60,
        "player_in": 100, "player_out": 200,
    }])
    sub_path = tmp_path / "subs.csv"
    subs.to_csv(sub_path, index=False)
    return sub_path, matches, events


def test_reconstructs_score_and_next_15_minute_outcome(tmp_path):
    event_rows = [
        {"eventName": "Shot", "tags": [{"id": 101}], "matchId": 10, "teamId": 1,
         "matchPeriod": "1H", "eventSec": 1200},
        {"eventName": "Shot", "tags": [{"id": 101}], "matchId": 10, "teamId": 2,
         "matchPeriod": "2H", "eventSec": 1100},
        {"eventName": "Shot", "tags": [{"id": 101}], "matchId": 10, "teamId": 1,
         "matchPeriod": "2H", "eventSec": 1000},
        {"eventName": "Shot", "tags": [], "matchId": 10, "teamId": 2,
         "matchPeriod": "2H", "eventSec": 600},
    ]
    sub_path, matches, events = _write_inputs(tmp_path, event_rows)

    result = build_match_state_table(sub_path, matches, events)

    row = result.iloc[0]
    assert row["home_score_at_substitution"] == 1
    assert row["away_score_at_substitution"] == 0
    assert row["team_goals_next_15"] == 1
    assert row["opponent_goals_next_15"] == 1
    assert row["outcome_label"] == "neutral"


def test_counts_free_kick_goal_and_credits_own_goal_to_opponent(tmp_path):
    event_rows = [
        {"eventName": "Free Kick", "tags": [{"id": 101}], "matchId": 10, "teamId": 1,
         "matchPeriod": "1H", "eventSec": 1200},
        {"eventName": "Others on the ball", "tags": [{"id": 102}], "matchId": 10, "teamId": 1,
         "matchPeriod": "2H", "eventSec": 1100},
        {"eventName": "Pass", "tags": [{"id": 1801}], "matchId": 10, "teamId": 2,
         "matchPeriod": "2H", "eventSec": 1000},
    ]
    sub_path, matches, events = _write_inputs(tmp_path, event_rows)

    result = build_match_state_table(sub_path, matches, events)
    row = result.iloc[0]

    assert row["home_score_at_substitution"] == 1
    assert row["away_score_at_substitution"] == 0
    assert row["team_goals_next_15"] == 0
    assert row["opponent_goals_next_15"] == 1
    assert row["outcome_label"] == "negative"


def test_rejects_non_positive_window(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="window_minutes"):
        build_match_state_table("missing.csv", tmp_path, tmp_path, 0)
