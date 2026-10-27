"""KICK-OFF substitution comparison prototype.

The current baseline uses match-state features only. Candidate IDs are collected
for the interface but are not model inputs, so both candidates receive the same
baseline probabilities until player/role features are engineered and validated.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from src.models.predict import predict_match_state

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "logistic_regression_baseline.joblib"
SUBSTITUTIONS_PATH = ROOT / "data" / "processed" / "substitutions.csv"


st.set_page_config(page_title="KICK-OFF | Substitution Lab", page_icon="⚽", layout="wide")
st.title("⚽ KICK-OFF")
st.caption("FOOTBALL INTELLIGENCE · DECISION SCIENCE · MACHINE LEARNING")
st.subheader("Substitution comparison lab")
st.write("Set the match situation and compare two possible replacements.")

if not MODEL_PATH.exists():
    st.error("Baseline model not found. Train it first with: python -m src.models.train_baseline")
    st.stop()

if not SUBSTITUTIONS_PATH.exists():
    st.error("Substitution data not found at data/processed/substitutions.csv.")
    st.stop()

try:
    substitutions = pd.read_csv(SUBSTITUTIONS_PATH)
    player_ids = sorted(
        set(substitutions["player_in"].dropna().astype(int))
        | set(substitutions["player_out"].dropna().astype(int))
    )
except (KeyError, ValueError, OSError) as exc:
    st.error(f"Could not load the substitution data: {exc}")
    st.stop()

with st.sidebar:
    st.header("Match situation")
    minute = st.slider("Match minute", 1, 90, 60)
    team_score = st.number_input("Your team's score", min_value=0, max_value=20, value=1)
    opponent_score = st.number_input("Opponent's score", min_value=0, max_value=20, value=1)
    team_side = st.selectbox("Your team", ["home", "away"])
    score_state = (
        "leading" if team_score > opponent_score
        else "trailing" if team_score < opponent_score
        else "level"
    )
    st.caption(f"Current state: **{score_state.title()}**")

st.markdown("### Candidate replacements")
left, right = st.columns(2)
default_a = player_ids[0] if player_ids else 0
default_b = player_ids[1] if len(player_ids) > 1 else default_a
with left:
    st.markdown("**Option A**")
    candidate_a = st.selectbox("Incoming player ID — A", player_ids, index=player_ids.index(default_a))
with right:
    st.markdown("**Option B**")
    candidate_b = st.selectbox("Incoming player ID — B", player_ids, index=player_ids.index(default_b))

if candidate_a == candidate_b:
    st.warning("Choose two different player IDs to compare two options.")

if st.button("Compare options", type="primary", use_container_width=True):
    try:
        model = __import__("joblib").load(MODEL_PATH)
        probabilities = predict_match_state(
            model,
            minute=minute,
            team_score=team_score,
            opponent_score=opponent_score,
            team_side=team_side,
            score_state=score_state,
        )
    except Exception as exc:
        st.error(f"Prediction failed: {exc}")
        st.stop()

    st.markdown("### Baseline outcome estimates")
    st.info(
        "Important research limitation: this baseline model only uses match state "
        "(minute, score, team side and score state). It does not use candidate-player "
        "attributes or roles. Therefore these probabilities are identical for A and B; "
        "they are context estimates, not evidence that either replacement is better."
    )
    cols = st.columns(2)
    for col, label, player_id in zip(cols, ["Option A", "Option B"], [candidate_a, candidate_b]):
        with col:
            st.markdown(f"#### {label} · Player {player_id}")
            for outcome in ["positive", "neutral", "negative"]:
                value = probabilities.get(outcome, 0.0)
                st.metric(f"{outcome.title()} outcome", f"{value:.1%}")
            st.caption("Same match-state baseline; no candidate-specific adjustment.")

    chart_data = pd.DataFrame(
        {"Outcome": list(probabilities), "Estimated probability": list(probabilities.values())}
    )
    st.bar_chart(chart_data.set_index("Outcome"))
    st.markdown("### Decision note")
    st.write(
        "The model cannot currently rank these two players. Use role suitability, "
        "fitness, tactical instructions and live match observation as separate "
        "human assessments until validated player-level features are added."
    )
else:
    st.caption("Enter the match context and select **Compare options** to view baseline estimates.")

st.divider()
st.caption(
    "Research prototype · Estimates are observational associations, not causal effects "
    "or guarantees. Outcome labels are provisional pending further validation."
)
