import json

from src.data.load_matches import load_match_directory, load_match_file


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
                        "malformed-entry",
                        {"minute": "not-a-minute", "playerIn": 503, "playerOut": 504},
                    ]
                },
            },
            "away": {
                "side": "away",
                "teamId": 22,
                "score": 1,
                "formation": {"substitutions": "null"},
            },
        },
    }


def test_load_match_file_extracts_match_and_valid_substitutions(tmp_path):
    source = tmp_path / "matches_England.json"
    source.write_text(json.dumps([_match()]), encoding="utf-8")

    frame = load_match_file(source)

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["match_id"] == 101
    assert row["home_team_id"] == 11
    assert row["away_team_id"] == 22
    assert row["home_score"] == 2
    assert row["away_score"] == 1
    assert row["home_substitutions"] == [
        {"minute": 60, "player_in": 501, "player_out": 502}
    ]
    assert row["away_substitutions"] == []


def test_load_match_file_accepts_matches_wrapper(tmp_path):
    source = tmp_path / "matches_Spain.json"
    source.write_text(json.dumps({"matches": [_match(202)]}), encoding="utf-8")

    frame = load_match_file(source)

    assert frame["match_id"].tolist() == [202]


def test_load_match_directory_combines_files_and_deduplicates(tmp_path):
    (tmp_path / "matches_England.json").write_text(
        json.dumps([_match(101), _match(102)]), encoding="utf-8"
    )
    (tmp_path / "matches_Spain.json").write_text(
        json.dumps([_match(102), _match(202)]), encoding="utf-8"
    )

    frame = load_match_directory(tmp_path)

    assert frame["match_id"].tolist() == [101, 102, 202]


def test_load_match_directory_raises_when_no_files_exist(tmp_path):
    try:
        load_match_directory(tmp_path)
    except FileNotFoundError as error:
        assert "matches_*.json" in str(error)
    else:
        raise AssertionError("Expected FileNotFoundError")
