"""KICK-OFF substitution comparison prototype."""
from pathlib import Path
import json
import joblib
import pandas as pd
import streamlit as st
from src.models.predict import predict_match_state

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/logistic_regression_baseline.joblib"
SUBS = ROOT / "data/processed/substitutions.csv"
PLAYERS = ROOT / "data/raw/players.json"

st.set_page_config(page_title="KICK-OFF | Substitution Lab", page_icon="⚽", layout="wide")
st.title("⚽ KICK-OFF")
st.caption("FOOTBALL INTELLIGENCE · DECISION SCIENCE · MACHINE LEARNING")
st.subheader("Substitution comparison lab")

if not MODEL.exists() or not SUBS.exists():
    st.error("Required files are missing. Follow the setup and training steps in the README.")
    st.stop()

subs = pd.read_csv(SUBS)
ids = sorted(set(subs.player_in.dropna().astype(int)) | set(subs.player_out.dropna().astype(int)))
profiles = {}
if PLAYERS.exists():
    try:
        players = json.loads(PLAYERS.read_text(encoding="utf-8"))
        for p in players:
            pid = p.get("wyId")
            if pid is None:
                continue
            name = p.get("shortName") or " ".join(
                x for x in [p.get("firstName"), p.get("middleName"), p.get("lastName")] if x
            ) or f"Player {pid}"
            role = p.get("role")
            position = role.get("name", "Not listed") if isinstance(role, dict) else "Not listed"
            profiles[int(pid)] = (name, position)
    except (OSError, ValueError, TypeError):
        st.warning("Player metadata could not be read; showing player IDs.")

def label(pid):
    return f"{profiles.get(int(pid), (f'Player {pid}', 'Not listed'))[0]} · #{pid}"

with st.sidebar:
    st.header("Match situation")
    minute = st.slider("Match minute", 1, 90, 60)
    team_score = st.number_input("Your team's score", 0, 20, 1)
    opponent_score = st.number_input("Opponent's score", 0, 20, 1)
    team_side = st.selectbox("Your team", ["home", "away"])
    state = "leading" if team_score > opponent_score else "trailing" if team_score < opponent_score else "level"
    st.caption(f"Score state: **{state.title()}**")

st.markdown("### Compare incoming players")
a, b = st.columns(2)
with a:
    st.markdown("**Option A**")
    player_a = st.selectbox("Incoming player A", ids, format_func=label, key="player_a")
with b:
    st.markdown("**Option B**")
    player_b = st.selectbox("Incoming player B", ids, index=min(1, len(ids)-1), format_func=label, key="player_b")

for col, pid in [(a, player_a), (b, player_b)]:
    name, position = profiles.get(int(pid), (f"Player {pid}", "Not listed"))
    with col:
        st.write(f"**{name}**")
        st.caption(f"Wyscout-listed position: {position}")

if player_a == player_b:
    st.warning("Select two different players to compare two options.")

if st.button("Compare match context", type="primary", use_container_width=True):
    model = joblib.load(MODEL)
    probs = predict_match_state(
        model, minute=minute, team_score=team_score, opponent_score=opponent_score,
        team_side=team_side, score_state=state,
    )
    st.markdown("### Estimated outcome for this match situation")
    st.info(
        "These probabilities use match minute, score, score difference and home/away "
        "status only. Player identity, position, role, fitness and manager data are not "
        "model inputs. The estimates are therefore identical for A and B and cannot "
        "identify a better replacement."
    )
    cols = st.columns(3)
    for col, outcome in zip(cols, ["positive", "neutral", "negative"]):
        col.metric(f"{outcome.title()} outcome", f"{probs.get(outcome, 0):.1%}")
    st.bar_chart(pd.DataFrame({"Probability": probs}).sort_index())
    st.markdown("### Decision summary")
    st.write(f"Option A: **{label(player_a)}** · Option B: **{label(player_b)}**")
    st.write(
        "Use listed position as basic player context, then assess tactical role, fitness "
        "and match observation separately. KICK-OFF does not yet calculate role fit or "
        "recommend a winner."
    )

st.divider()
st.caption(
    "Research prototype. Historical associations are not causal effects or guarantees. "
    "Outcome labels remain provisional pending further validation."
)
