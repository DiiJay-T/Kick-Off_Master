import json

from src.data.validate_matches import validate_match_files


def _match(match_id, substitutions):
    return {
        "wyId": match_id,
        "dateutc": "2018-05-01T19:00:00Z",
        "competitionId": 3,
        "seasonId": 4,
        "teamsData": {
            "home": {
                "teamId": 11,
                "side": "home",
                "score": 2,
                "formation": {"substitutions": substitutions},
            },
            "away": {
                "teamId": 22,
                "side": "away",
                "score": 1,
                "formation": {"substitutions": []},
            },
        },
    }


def test_validation_counts_valid_malformed_missing_and_duplicate_data(tmp_path):
    first = tmp_path / "matches_England.json"
    second = tmp_path / "matches_Spain.json"

    first.write_text(
        json.dumps(
            [
                _match(
                    100,
                    [
                        {"minute": 60, "playerIn": 501, "playerOut": 502},
                        {"minute": "bad", "playerIn": 503, "playerOut": 504},
                        "not-an-object",
                    ],
                )
            ]
        ),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps([_match(100, "unexpected-string"), _match(200, [])]),
        encoding="utf-8",
    )

    report = validate_match_files(tmp_path)

    assert report["files_inspected"] == 2
    assert report["total_matches"] == 3
    assert report["unique_match_ids"] == 2
    assert report["duplicate_match_ids"] == 1
    assert report["valid_substitutions"] == 1
    assert report["malformed_substitutions"] == 3
    assert report["substitution_field_errors"]["invalid_minute"] == 1
    assert report["substitution_field_errors"]["entry_not_an_object"] == 1
    assert report["substitution_field_errors"]["substitutions_not_a_list"] == 1


def test_validation_reports_missing_fields(tmp_path):
    source = tmp_path / "matches_England.json"
    source.write_text(json.dumps([{"wyId": 1}]), encoding="utf-8")

    report = validate_match_files(tmp_path)

    assert report["missing_match_fields"]["dateutc"] == 1
    assert report["missing_match_fields"]["teamsData"] == 1


def test_validation_does_not_modify_source_file(tmp_path):
    source = tmp_path / "matches_England.json"
    original = json.dumps([_match(300, [])])
    source.write_text(original, encoding="utf-8")

    validate_match_files(tmp_path)

    assert source.read_text(encoding="utf-8") == original
