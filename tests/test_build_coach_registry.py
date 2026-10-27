import json

from src.data.build_coach_registry import (
    extract_coach_appearances, load_team_names, summarize_coaches,
)


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
    appearances = extract_coach_appearances(
        tmp_path, {10: "Home FC", 20: "Away FC"}
    )
    registry = summarize_coaches(appearances)
    assert len(appearances) == 4
    assert appearances.iloc[0]["team_name"] == "Home FC"
    assert appearances.iloc[0]["opponent_name"] == "Away FC"
    row = registry.set_index("coach_id").loc[100]
    assert row["match_appearances"] == 2
    assert row["team_ids"] == "10"
    assert row["team_names"] == "Home FC"
    assert row["first_match_date"].startswith("2018-01-01")
    assert row["last_match_date"].startswith("2018-02-01")


def test_loads_team_names_by_wyscout_id(tmp_path):
    source = tmp_path / "teams.json"
    source.write_text(json.dumps([
        {"wyId": 10, "name": "Home FC", "officialName": "Home Football Club"},
        {"wyId": 20, "name": "Away FC"},
    ]), encoding="utf-8")
    assert load_team_names(source) == {10: "Home FC", 20: "Away FC"}
