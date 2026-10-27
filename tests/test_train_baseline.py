import pandas as pd

from src.models.train_baseline import prepare_model_table


def test_prepare_model_table_uses_only_pre_outcome_features(tmp_path):
    path = tmp_path / "match_state.csv"
    pd.DataFrame([
        {
            "match_id": 1,
            "minute": 60,
            "team_score_at_substitution": 1,
            "opponent_score_at_substitution": 0,
            "team_side": "home",
            "score_state": "leading",
            "team_goals_next_15": 1,
            "opponent_goals_next_15": 0,
            "goal_difference_next_15": 1,
            "outcome_label": "positive",
        },
        {
            "match_id": 2,
            "minute": 75,
            "team_score_at_substitution": 0,
            "opponent_score_at_substitution": 2,
            "team_side": "away",
            "score_state": "trailing",
            "team_goals_next_15": 0,
            "opponent_goals_next_15": 1,
            "goal_difference_next_15": -1,
            "outcome_label": "negative",
        },
    ]).to_csv(path, index=False)

    result = prepare_model_table(path)

    assert "score_difference_at_substitution" in result.columns
    assert result["score_difference_at_substitution"].tolist() == [1, -2]
    assert "goal_difference_next_15" in result.columns
