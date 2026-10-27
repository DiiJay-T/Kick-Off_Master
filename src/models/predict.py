"""Prediction helpers for the match-state baseline."""

from __future__ import annotations

import pandas as pd


def build_match_state_features(
    *, minute: int, team_score: int, opponent_score: int,
    team_side: str, score_state: str,
) -> pd.DataFrame:
    """Build exactly the pre-outcome features expected by the baseline pipeline."""
    if team_side not in {"home", "away"}:
        raise ValueError("team_side must be 'home' or 'away'")
    if score_state not in {"leading", "level", "trailing"}:
        raise ValueError("score_state must be leading, level or trailing")
    return pd.DataFrame([{
        "minute": minute,
        "team_score_at_substitution": team_score,
        "opponent_score_at_substitution": opponent_score,
        "score_difference_at_substitution": team_score - opponent_score,
        "team_side": team_side,
        "score_state": score_state,
    }])


def predict_match_state(model, **match_state) -> dict[str, float]:
    """Return outcome probabilities from a fitted baseline pipeline."""
    features = build_match_state_features(**match_state)
    values = model.predict_proba(features)[0]
    classes = model.named_steps["classifier"].classes_
    return {str(label): float(probability) for label, probability in zip(classes, values)}
