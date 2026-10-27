import pandas as pd
import pytest

from src.models.predict import build_match_state_features


def test_build_match_state_features_derives_score_difference():
    row = build_match_state_features(
        minute=67, team_score=2, opponent_score=1,
        team_side="home", score_state="leading",
    ).iloc[0]
    assert row["score_difference_at_substitution"] == 1
    assert row["minute"] == 67


def test_build_match_state_features_rejects_invalid_side():
    with pytest.raises(ValueError):
        build_match_state_features(
            minute=50, team_score=0, opponent_score=0,
            team_side="neutral", score_state="level",
        )
