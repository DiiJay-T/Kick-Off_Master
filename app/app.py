"""KICK-OFF — football substitution decision-support prototype."""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from src.models.predict import predict_match_state

st.set_page_config(page_title="KICK-OFF | Substitution Lab", page_icon="⚽", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#eaf0f6; --muted:#91a0b2; --panel:#111d2b; --line:#263648; --lime:#c8f169; }
html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
.stApp { background: radial-gradient(ellipse at 75% 0%, #1c3440 0%, #0a1420 48%, #08111b 100%); color:var(--ink); }
.block-container { max-width:1240px; padding-top:2.1rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#0c1723; border-right:1px solid #263648; }
[data-testid="stSidebar"] * { color:#eaf0f6; }
.eyebrow { color:var(--lime); font-family:'DM Mono',monospace; letter-spacing:.18em; font-size:.72rem; }
.hero { padding:1.6rem 0 1.3rem 0; border-bottom:1px solid var(--line); margin-bottom:1.5rem; }
.hero h1 { font-size:3.1rem; font-weight:800; letter-spacing:-.07em; line-height:1; margin:.45rem 0; color:#f4f7fa; }
.hero p { color:#9cabb9; font-size:.9rem; letter-spacing:.11em; }
.section-label { color:var(--lime); font-family:'DM Mono',monospace; font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; margin:1.2rem 0 .7rem; }
.panel { background:linear-gradient(145deg,rgba(22,37,53,.96),rgba(13,25,38,.96)); border:1px solid var(--line); border-radius:16px; padding:1.2rem 1.3rem; min-height:125px; }
.panel-kicker { color:#91a0b2; font-family:'DM Mono',monospace; font-size:.68rem; letter-spacing:.12em; text-transform:uppercase; }
.panel-title { color:#f1f5f8; font-size:1.15rem; font-weight:800; margin:.45rem 0 .2rem; }
.panel-sub { color:#9cabb9; font-size:.82rem; }
.pill { display:inline-block; border:1px solid #496044; color:var(--lime); border-radius:99px; padding:.22rem .65rem; font-family:'DM Mono',monospace; font-size:.68rem; }
.note { background:#142332; border-left:3px solid var(--lime); padding:1rem 1.1rem; border-radius:0 10px 10px 0; color:#b9c5d0; font-size:.88rem; }
div.stButton > button[kind="primary"] { background:var(--lime); color:#101a21; border:0; border-radius:10px; font-weight:800; min-height:3rem; }
div.stButton > button[kind="primary"]:hover { background:#d8ff8b; color:#101a21; }
h2,h3 { color:#f1f5f8 !important; }
[data-testid="stMetric"] { background:#111d2b; border:1px solid #263648; border-radius:12px; padding:1rem; }
[data-testid="stMetricLabel"] { color:#a5b2bf !important; }
[data-testid="stMetricValue"] { color:#f1f5f8 !important; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { background:#111d2b; border-color:#34485b; }
hr { border-color:#263648; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="eyebrow">FOOTBALL INTELLIGENCE · DECISION SCIENCE · MACHINE LEARNING</div>
  <h1>KICK-OFF<span style="color:#c8f169">.</span></h1>
  <p>SUBSTITUTION LAB &nbsp; / &nbsp; MATCH-STATE ANALYSIS</p>
  <span class="pill">RESEARCH PROTOTYPE · BASELINE MODEL</span>
</div>
""", unsafe_allow_html=True)

MODEL = ROOT / "models/logistic_regression_baseline.joblib"
SUBS = ROOT / "data/processed/substitutions.csv"
PLAYERS = ROOT / "data/raw/players.json"
COACHES = ROOT / "data/processed/coach_appearances.csv"
MANAGERS = ROOT / "data/reference/manager_profiles.json"

if not MODEL.exists() or not SUBS.exists():
    st.error("Required files are missing. Follow the setup and training steps in the README.")
    st.stop()

subs = pd.read_csv(SUBS)
ids = sorted(set(subs.player_in.dropna().astype(int)) | set(subs.player_out.dropna().astype(int)))
if not ids:
    st.error("No player IDs were found in the substitution dataset.")
    st.stop()

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


# Curated tactical descriptors are qualitative references, not measured team metrics.
TACTICAL_ARCHETYPES = {
    "forward": {"Attacking threat": 5, "Possession link": 2, "Defensive work": 1, "Transition threat": 4},
    "winger": {"Attacking threat": 4, "Possession link": 3, "Defensive work": 2, "Transition threat": 5},
    "midfield": {"Attacking threat": 3, "Possession link": 5, "Defensive work": 3, "Transition threat": 3},
    "defender": {"Attacking threat": 1, "Possession link": 3, "Defensive work": 5, "Transition threat": 2},
    "goalkeeper": {"Attacking threat": 0, "Possession link": 2, "Defensive work": 5, "Transition threat": 1},
    "unknown": {"Attacking threat": 0, "Possession link": 0, "Defensive work": 0, "Transition threat": 0},
}
def archetype(position):
    p = str(position).lower()
    if "goalkeeper" in p: return "goalkeeper"
    if any(x in p for x in ["forward", "striker", "attacker"]): return "forward"
    if any(x in p for x in ["wing", "wide"]): return "winger"
    if any(x in p for x in ["midfield", "midfielder"]): return "midfield"
    if any(x in p for x in ["defender", "back"]): return "defender"
    return "unknown"

def skill_web_figure(position):
    values = TACTICAL_ARCHETYPES[archetype(position)]
    keys = list(values)
    fig = go.Figure(go.Scatterpolar(r=[values[k] for k in keys], theta=keys,
        fill="toself", line_color="#c8f169", fillcolor="rgba(200,241,105,.18)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,5], gridcolor="#34485b"),
        angularaxis=dict(gridcolor="#34485b")), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#eaf0f6", margin=dict(l=35,r=35,t=20,b=20), height=300)
    return fig

def plausible_effect(position, state, minute):
    role = archetype(position)
    effects = {
      "forward": ("Attacking outlet", "Offers a higher target and more penalty-area presence; may reduce midfield link play.", "If chasing the game, extra forward presence can increase box occupation. It can also leave fewer players connecting midfield."),
      "winger": ("Width and transition", "Can stretch the back line and provide a direct ball-carrying outlet; defensive tracking may vary.", "A wide runner may help attack space quickly, but possession can become less secure if attacks are rushed."),
      "midfield": ("Control and circulation", "May add passing options and help connect phases; attacking depth depends on the player's actual profile.", "An extra central option can help retain the ball and manage tempo, especially when protecting a lead."),
      "defender": ("Defensive security", "Adds a natural defensive profile and may strengthen box protection; could reduce forward numbers.", "A defensive profile may support a narrow lead, while increasing attacking pressure can become harder if a forward is removed."),
      "goalkeeper": ("Goalkeeping role", "A goalkeeper is not a like-for-like outfield replacement; this option needs a specialist review.", "No outfield tactical effect is inferred for a goalkeeper substitution."),
      "unknown": ("Insufficient position evidence", "The source-listed position is unavailable or too broad to assign a reliable role archetype.", "KICK-OFF will not invent a skill profile when position evidence is missing."),
    }
    return effects[role]

def player_label(pid):
    return f"{profiles.get(int(pid), (f'Player {pid}', 'Not listed'))[0]}  ·  #{pid}"

with st.sidebar:
    st.markdown('<div class="eyebrow">01 / MATCH CONTEXT</div>', unsafe_allow_html=True)
    st.markdown("## Set the situation")
    minute = st.slider("Match minute", 1, 90, 60)
    st.markdown("**Current score**")
    score_cols = st.columns(2)
    with score_cols[0]:
        team_score = st.number_input("Your team", 0, 20, 1)
    with score_cols[1]:
        opponent_score = st.number_input("Opponent", 0, 20, 1)
    team_side = st.selectbox("Team location", ["home", "away"])
    state = "leading" if team_score > opponent_score else "trailing" if team_score < opponent_score else "level"
    st.markdown(f'<div class="panel"><div class="panel-kicker">LIVE MATCH STATE</div><div class="panel-title">{state.upper()}</div><div class="panel-sub">Minute {minute} &nbsp;·&nbsp; {team_score} – {opponent_score}</div></div>', unsafe_allow_html=True)
    st.caption("Context is supplied manually for this prototype.")

st.markdown('<div class="section-label">02 / PLAYER SHORTLIST</div>', unsafe_allow_html=True)
st.markdown("### Compare two possible replacements")
st.caption("Choose two players from the historical Wyscout substitution records.")

a, b = st.columns(2, gap="large")
with a:
    st.markdown('<div class="panel-kicker">OPTION A</div>', unsafe_allow_html=True)
    player_a = st.selectbox("First incoming player", ids, format_func=player_label, key="player_a")
    name_a, pos_a = profiles.get(int(player_a), (f"Player {player_a}", "Not listed"))
    st.markdown(f'<div class="panel"><div class="panel-kicker">PLAYER PROFILE</div><div class="panel-title">{name_a}</div><div class="panel-sub">{pos_a} &nbsp;·&nbsp; Wyscout-listed position</div></div>', unsafe_allow_html=True)
with b:
    st.markdown('<div class="panel-kicker">OPTION B</div>', unsafe_allow_html=True)
    default_b = min(1, len(ids) - 1)
    player_b = st.selectbox("Second incoming player", ids, index=default_b, format_func=player_label, key="player_b")
    name_b, pos_b = profiles.get(int(player_b), (f"Player {player_b}", "Not listed"))
    st.markdown(f'<div class="panel"><div class="panel-kicker">PLAYER PROFILE</div><div class="panel-title">{name_b}</div><div class="panel-sub">{pos_b} &nbsp;·&nbsp; Wyscout-listed position</div></div>', unsafe_allow_html=True)


st.markdown('<div class="section-label">03 / TACTICAL INTELLIGENCE</div>', unsafe_allow_html=True)
coach_df = pd.read_csv(COACHES) if COACHES.exists() else pd.DataFrame()
manager_data = json.loads(MANAGERS.read_text(encoding="utf-8")) if MANAGERS.exists() else {"profiles":[]}
team_options = sorted(coach_df.team_name.dropna().astype(str).unique()) if not coach_df.empty else []
selected_team = st.selectbox("Team / manager context", ["Not specified"] + team_options)
if selected_team != "Not specified" and not coach_df.empty:
    team_rows = coach_df[coach_df.team_name.astype(str) == selected_team]
    coach_ids = sorted(team_rows.coach_id.dropna().astype(int).unique())
    st.caption(f"Dataset records {len(team_rows)} coach appearances for {selected_team}; coach IDs: {', '.join(map(str, coach_ids))}. This is match-record identity, not a verified public manager name.")
    reference = next((x for x in manager_data.get("profiles",[]) if x.get("team_name","").lower() == selected_team.lower()), None)
    if reference:
        st.info(f"**2017/18 tactical reference — {reference['manager_name']}:** {reference['qualitative_summary']}  
Tags: {', '.join(reference.get('tactical_tags', []))}  
This team-season reference is not automatically matched to the coach IDs above.")
    else:
        st.info("No curated manager strategy is available for this team. The match-level coach ID is retained without guessing a manager identity or tactical philosophy.")
else:
    st.caption("Select a team to inspect the recorded coach IDs and any available curated strategy reference.")


if player_a == player_b:
    st.warning("Choose two different players to make the comparison meaningful.")

run = st.button("ANALYSE MATCH CONTEXT  →", type="primary", use_container_width=True, disabled=(player_a == player_b))
if run:
    model = joblib.load(MODEL)
    probs = predict_match_state(
        model, minute=minute, team_score=team_score, opponent_score=opponent_score,
        team_side=team_side, score_state=state,
    )
    st.markdown('<div class="section-label">03 / MODEL OUTPUT</div>', unsafe_allow_html=True)
    st.markdown("### Estimated outcome probabilities")
    st.markdown('<div class="note">These estimates describe the match context only. The baseline model uses minute, score, score difference and home/away status. It does <b>not</b> use player identity, position, role, fitness or manager data. Therefore, the probabilities are the same for both options and do not identify a better replacement.</div>', unsafe_allow_html=True)
    metrics = st.columns(3)
    for col, outcome in zip(metrics, ["positive", "neutral", "negative"]):
        col.metric(f"{outcome.title()} outcome", f"{probs.get(outcome, 0):.1%}")
    chart = pd.DataFrame({"Estimated probability": [probs.get(k, 0) for k in ["positive", "neutral", "negative"]]}, index=["Positive", "Neutral", "Negative"])
    st.bar_chart(chart, use_container_width=True)
    st.markdown('<div class="section-label">04 / PLAYER SKILL WEB</div>', unsafe_allow_html=True)
    st.caption("These are illustrative position-archetype tendencies, not measured individual player ratings. Individual event-derived skills are a future layer.")
    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"**OPTION A · {name_a}**")
        st.plotly_chart(skill_web_figure(pos_a), use_container_width=True, config={"displayModeBar":False})
    with cb:
        st.markdown(f"**OPTION B · {name_b}**")
        st.plotly_chart(skill_web_figure(pos_b), use_container_width=True, config={"displayModeBar":False})
    st.markdown('<div class="section-label">05 / PLAUSIBLE MATCH EFFECT</div>', unsafe_allow_html=True)
    ea, eb = st.columns(2)
    for col, label, position in [(ea, "OPTION A", pos_a), (eb, "OPTION B", pos_b)]:
        heading, tradeoff, explanation = plausible_effect(position, state, minute)
        with col:
            st.markdown(f'<div class="panel"><div class="panel-kicker">{label} · TACTICAL HYPOTHESIS</div><div class="panel-title">{heading}</div><div class="panel-sub">{tradeoff}</div></div>', unsafe_allow_html=True)
            st.write(explanation)
    st.info("These effects are transparent tactical heuristics based on listed position and match state. They are hypotheses for a manager to assess, not observed player-specific effects or causal predictions.")

st.divider()
st.markdown('<div class="eyebrow">KICK-OFF / MODEL NOTES</div>', unsafe_allow_html=True)
st.caption("Historical associations are not causal effects or guarantees. Outcome labels are provisional pending further validation. Built as an educational decision-support research prototype.")
