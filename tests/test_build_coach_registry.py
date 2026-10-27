import json

from src.data.build_coach_registry import extract_coach_appearances, summarize_coaches


def _match(match_id, date, home_coach, away_coach):
    return {
        "wyId": match_id, "dateutc": date, "label": "A - B",
        "teamsData": {
            "home": {"side": "home", "teamId": 10, "coachId": home_coach, "score": 1},
            "away": {"side": "away", "teamId": 20, "coachId": away_coach, "score": 0},
        },
    }


def test_extracts_match_level_coach_ids_and_summarizes_tenure(tmp_path):
    (tmp_path / "matches_England.json").write_text(json.dumps([
        _match(1, "2018-01-01T00:00:00Z", 100, 200),
        _match(2, "2018-02-01T00:00:00Z", 100, 201),
    ]), encoding="utf-8")
    appearances = extract_coach_appearances(tmp_path)
    registry = summarize_coaches(appearances)
    assert len(appearances) == 4
    row = registry.set_index("coach_id").loc[100]
    assert row["match_appearances"] == 2
    assert row["team_ids"] == "10"
    assert row["first_match_date"].startswith("2018-01-01")
    assert row["last_match_date"].startswith("2018-02-01")
