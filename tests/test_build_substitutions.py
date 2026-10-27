import json

import pytest

from src.data.build_substitutions import (
    SUBSTITUTION_COLUMNS,
    build_substitution_table,
)


def _match(match_id=101):
    return {
        "wyId": match_id,
        "label": "Home FC - Away FC",
        "date": "2018-05-01 20:00:00",
        "dateutc": "2018-05-01T19:00:00Z",
        "competitionId": 3,
        "seasonId": 4,
        "gameweek": 10,
        "status": "Played",
        "duration": "Regular",
        "winner": 11,
        "teamsData": {
            "home": {
                "side": "home",
                "teamId": 11,
                "score": 2,
                "formation": {
                    "substitutions": [
                        {"minute": 60, "playerIn": 501, "playerOut": 502},
                        {"minute": 75, "playerIn": 503, "playerOut": 504},
                        "malformed",
                    ]
                },
            },
            "away": {
                "side": "away",
                "teamId": 22,
                "score": 1,
                "formation": {
                    "substitutions": [
                        {"minute": 80, "playerIn": 601, "playerOut": 602}
                    ]
                },
            },
        },
    }


def test_builds_one_row_per_valid_substitution_and_preserves_context(tmp_path):
    source = tmp_path / "matches_England.json"
    source.write_text(json.dumps([_match()]), encoding="utf-8")

    table = build_substitution_table(tmp_path)

    assert len(table) == 3
    assert list(table.columns) == SUBSTITUTION_COLUMNS
    assert table["match_id"].tolist() == [101, 101, 101]
    assert table["team_side"].tolist() == ["home", "home", "away"]
    assert table["team_id"].tolist() == [11, 11, 22]
    assert table["minute"].tolist() == [60, 75, 80]
    assert table["player_in"].tolist() == [501, 503, 601]
    assert table["player_out"].tolist() == [502, 504, 602]
    assert table["competition"].tolist() == ["England"] * 3
    assert table["final_home_score"].tolist() == [2, 2, 2]


def test_deduplicates_match_ids_across_files(tmp_path):
    (tmp_path / "matches_England.json").write_text(
        json.dumps([_match(101)]), encoding="utf-8"
    )
    (tmp_path / "matches_Spain.json").write_text(
        json.dumps([_match(101), _match(202)]), encoding="utf-8"
    )

    table = build_substitution_table(tmp_path)

    assert set(table["match_id"]) == {101, 202}
    assert len(table) == 6


def test_returns_empty_table_with_headers_when_no_substitutions(tmp_path):
    match = _match()
    match["teamsData"]["home"]["formation"]["substitutions"] = []
    match["teamsData"]["away"]["formation"]["substitutions"] = []
    (tmp_path / "matches_England.json").write_text(
        json.dumps([match]), encoding="utf-8"
    )

    table = build_substitution_table(tmp_path)

    assert table.empty
    assert list(table.columns) == SUBSTITUTION_COLUMNS


def test_raises_when_match_files_are_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"matches_\*\.json"):
        build_substitution_table(tmp_path)
