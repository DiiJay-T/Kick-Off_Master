"""KICK-OFF — football substitution decision-support prototype."""
from pathlib import Path
import sys
import json
import re

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from src.models.predict import predict_match_state
from src.data.player_identity import clean_player_display_name

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
FIFA_PROFILES = ROOT / "data/processed/player_fifa18_profiles.csv"

if not MODEL.exists() or not SUBS.exists():
    st.error("Required files are missing. Follow the setup and training steps in the README.")
    st.stop()

subs = pd.read_csv(SUBS)
ids = sorted(set(subs.player_in.dropna().astype(int)) | set(subs.player_out.dropna().astype(int)))
if not ids:
    st.error("No player IDs were found in the substitution dataset.")
    st.stop()

fifa_profiles = {}
fifa_profiles_by_id = {}
if FIFA_PROFILES.exists():
    try:
        fifa_df = pd.read_csv(FIFA_PROFILES)
        for _, row in fifa_df.iterrows():
            record = row.to_dict()
            try:
                fifa_profiles_by_id[int(row["wy_id"])] = record
            except (KeyError, TypeError, ValueError):
                pass
            for alias in (row.get("wyscout_name", ""), row.get("wyscout_display_name", "")):
                key = " ".join(str(alias).strip().lower().split())
                if key:
                    fifa_profiles[key] = record
        if fifa_df.empty:
            st.warning("The FIFA profile file exists but contains no matched players.")
    except (OSError, ValueError, TypeError) as exc:
        st.warning(f"FIFA 18 profiles could not be read ({exc}); using position proxies.")
else:
    st.warning("FIFA 18 profile file is missing. Run scripts/build_fifa18_profiles.py to generate it.")

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
            # Remove obvious numeric export suffixes from display labels only.
            # Keep the raw Wyscout source untouched and retain the stable player ID.
            name = clean_player_display_name(name)
            if not name or not re.search(r"[A-Za-zÀ-ÿ]", name):
                continue
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
        fill="toself", line=dict(color="#ffb000", width=4),
        fillcolor="rgba(255,176,0,.32)", marker=dict(size=7, color="#ff5e3a")))
    fig.update_layout(polar=dict(bgcolor="rgba(15,25,42,.55)",
        radialaxis=dict(visible=True, range=[0,5], gridcolor="#53647d", tickfont=dict(color="#dce7f5")),
        angularaxis=dict(gridcolor="#53647d", tickfont=dict(color="#f2f6ff"))),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f2f6ff", margin=dict(l=45,r=45,t=24,b=24), height=320)
    return fig

PLAYER_ROLE_REFERENCES = {
    "kylian mbappe": ("Depth-running / transition forward", "Explosive acceleration, carries into open space and threatens the channel behind the defensive line.", "Best suited to space to attack; a deep block can reduce the value of his running lanes."),
    "robert lewandowski": ("Penalty-box reference striker", "Central occupation, timing across the defensive line, finishing and combination play around the box.", "Needs service into dangerous central areas; a low-touch role far from the box can underuse this profile."),
    "lionel messi": ("Creative free-roaming forward", "Receives between lines, carries centrally, creates through passes and can finish after moving infield.", "Needs freedom and runners ahead; teammates may need to preserve width and cover transition spaces."),
    "roberto firmino": ("Dropping / connective forward", "Drops into midfield pockets, links combinations and creates space for runners beyond him.", "Works best with runners attacking the space he vacates; may offer less penalty-box occupation than a fixed number nine.")
}

# Every player receives a role hypothesis. Known players get a named reference;
# all other players get a position-specific sub-role inferred cautiously from
# FIFA 18 attribute shape when available, otherwise a transparent role default.
def player_role_hypothesis(name, position, player_id=None):
    key = " ".join(str(name).lower().replace(".", "").split())
    for known, detail in PLAYER_ROLE_REFERENCES.items():
        if known in key or key in known:
            return detail
    role = archetype(position)
    record = fifa_profiles_by_id.get(int(player_id)) if player_id is not None else None
    if not record:
        record = fifa_profiles.get(key)
    def score(field):
        try:
            value = float(record.get(field))
            return value if pd.notna(value) else None
        except (AttributeError, TypeError, ValueError):
            return None
    pace, shooting, passing = score("fifa_pace"), score("fifa_shooting"), score("fifa_passing")
    dribbling, defending, physical = score("fifa_dribbling"), score("fifa_defending"), score("fifa_physical")
    if role == "forward":
        if pace is not None and pace >= 80 and (dribbling or 0) >= 70:
            return ("Depth-running / transition forward", "Attribute shape suggests pace and ball-carrying may support runs beyond the line and attacks into open channels.", "This is a FIFA-card-based hypothesis; verify runs in behind and carries from Wyscout events.")
        if passing is not None and passing >= 75 and (dribbling or 0) >= 75:
            return ("Creative / dropping forward", "Attribute shape suggests a forward who may connect play, receive between lines and create for runners.", "Card ratings do not prove a false-nine role; confirm touches, passes and positioning in match data.")
        if shooting is not None and shooting >= 78:
            return ("Box-focused finishing forward", "Attribute shape suggests a player whose value may centre on finishing and occupying high-value shooting zones.", "Shot locations, touches in the box and chance quality are needed to validate this hypothesis.")
        return ("Central / channel forward", "Can occupy the last line, attack central finishing zones or threaten channels depending on team structure.", "The available data does not yet separate a target striker, runner, poacher or link forward.")
    if role == "winger":
        if pace is not None and pace >= 80 and (dribbling or 0) >= 75:
            return ("1v1 ball-carrying winger", "Attribute shape suggests acceleration and dribbling suited to isolations, carries and attacking the space behind full-backs.", "Preferred foot, crossing frequency and successful take-ons are needed to distinguish an outside winger from an inverted winger.")
        if passing is not None and passing >= 75:
            return ("Creative wide playmaker", "Attribute shape suggests a wide player who may create through combinations, crosses or passes into central areas.", "Actual chance creation and crossing locations must be checked in event data.")
        return ("Width / channel winger", "Can stretch the pitch, receive wide and attack the channel between full-back and centre-back.", "The player's tendency to stay wide or move inside is not established by position alone.")
    if role == "midfield":
        if defending is not None and defending >= 70 and physical is not None and physical >= 70:
            return ("Ball-winning / screening midfielder", "Attribute shape suggests defensive duels, screening and protection in front of the back line.", "Confirm recoveries, interceptions, defensive duels and positioning; card ratings are not event evidence.")
        if passing is not None and passing >= 78:
            return ("Deep distributor / playmaker", "Attribute shape suggests a passer who may dictate circulation and progress possession from deeper zones.", "Confirm progressive passes, switches, forward-pass share and pressure resistance.")
        if shooting is not None and shooting >= 70 and physical is not None and physical >= 70:
            return ("Box-to-box / arriving midfielder", "Attribute shape suggests a midfielder who may combine physical coverage with late attacking arrivals.", "Confirm distance/coverage proxies, box entries and timing of attacking runs before assigning this role.")
        return ("Central connector", "Can link possession, support progression and contribute to defensive coverage between the lines.", "The source position does not establish whether this player is a holder, runner or advanced creator.")
    if role == "defender":
        if pace is not None and pace >= 75 and passing is not None and passing >= 65:
            return ("Progressive / recovery defender", "Attribute shape suggests recovery speed and some capacity to advance or distribute from the back.", "Need observed defensive line position, carries and progressive passing to distinguish full-back, wide centre-back or covering centre-back.")
        if defending is not None and defending >= 75 and physical is not None and physical >= 75:
            return ("Duel-focused central defender", "Attribute shape suggests strength in physical defending and direct defensive contests.", "Confirm aerial and ground-duel volume, success, clearances and defensive positioning.")
        if passing is not None and passing >= 75:
            return ("Build-up distributor", "Attribute shape suggests a defender who may help initiate possession and break the first press.", "Confirm progressive passes, line-breaking passes and turnovers under pressure.")
        return ("Defensive-line / support defender", "Supports line protection, duels and progression from deeper areas.", "A defender label alone cannot distinguish centre-back, full-back or wing-back responsibilities.")
    if role == "goalkeeper":
        return ("Goalkeeper / sweeper-keeper hypothesis", "Specialist goalkeeper role; distribution and starting position would distinguish a conventional keeper from a sweeper-keeper.", "Outfield attributes cannot establish goalkeeper style; goalkeeper-specific events and starting-position data are required.")
    return ("Role not established", "The source position is unavailable or too broad to assign a reliable tactical sub-role.", "Keep the hypothesis unclassified until player position or match deployment evidence is available.")

def plausible_effect(position, state, minute, name="", player_id=None):
    return player_role_hypothesis(name, position, player_id)


def player_label(pid):
    return f"{profiles.get(int(pid), (f'Player {pid}', 'Not listed'))[0]}  ·  #{pid}"

PLAYER_STYLE_REFERENCES = {
    "roberto firmino": {
        "values": {"Attacking threat": 3.6, "Playmaking": 4.8, "Link-up play": 4.9, "Defensive work": 3.1, "Transition": 3.8},
        "summary": "A forward who often drops between the lines, links combinations and creates space for runners. His striker label alone understates his connective playmaking role.",
        "source_note": "Qualitative 2017/18 role reference; values are KICK-OFF interpretation, not official FIFA attributes.",
        "impact_flag": True,
        "flag_reason": "A curated high-impact role reference; the flag is editorial, not a model prediction."
    }
}
MANAGER_DIMENSIONS = ["Possession", "Pressing", "Directness", "Defensive structure", "Positional rotation"]
TAG_DIMENSIONS = {
    "possession_dominance": "Possession", "possession": "Possession", "positional_play": "Positional rotation",
    "structured_counterpress": "Pressing", "counterpress": "Pressing", "high_press": "Pressing",
    "fast_transitions": "Directness", "vertical_attacking": "Directness", "direct_play": "Directness",
    "compact_defence": "Defensive structure", "structured_defence": "Defensive structure",
    "back_three": "Defensive structure", "inverted_fullbacks": "Positional rotation",
    "central_overloads": "Positional rotation", "formation_flexibility": "Positional rotation"
}
MANAGER_STYLE_REFERENCES = {
    "pep guardiola": {"impact_flag": True, "flag_reason": "Sustained elite team-level performance in the documented reference season."},
    "jürgen klopp": {"impact_flag": True, "flag_reason": "Sustained elite team-level performance in the documented reference season."},
    "jurgen klopp": {"impact_flag": True, "flag_reason": "Sustained elite team-level performance in the documented reference season."}
}

def named_player_reference(name):
    return PLAYER_STYLE_REFERENCES.get(str(name).strip().lower())

def player_web_figure(position, name, player_id=None):
    reference = named_player_reference(name)
    fifa = fifa_profiles_by_id.get(int(player_id)) if player_id is not None else None
    fifa = fifa or fifa_profiles.get(" ".join(str(name).strip().lower().split()))
    if fifa:
        values = {
            "Attacking threat": (float(fifa.get("fifa_shooting", 0)) + float(fifa.get("fifa_dribbling", 0))) / 40,
            "Playmaking": float(fifa.get("fifa_passing", 0)) / 20,
            "Link-up play": (float(fifa.get("fifa_passing", 0)) + float(fifa.get("fifa_dribbling", 0))) / 40,
            "Defensive work": float(fifa.get("fifa_defending", 0)) / 20,
            "Transition": (float(fifa.get("fifa_pace", 0)) + float(fifa.get("fifa_physical", 0))) / 40
        }
        label = "FIFA 18 card-derived profile"
    elif reference:
        values = reference["values"]
        label = "Curated named-player role reference"
    else:
        base = TACTICAL_ARCHETYPES[archetype(position)]
        values = {"Attacking threat": base["Attacking threat"], "Playmaking": base["Possession link"],
                  "Link-up play": base["Possession link"], "Defensive work": base["Defensive work"],
                  "Transition": base["Transition threat"]}
        label = "Position archetype proxy"
    values = {key: max(0.0, min(5.0, float(pd.to_numeric(value, errors="coerce"))))
              if pd.notna(pd.to_numeric(value, errors="coerce")) else 0.0
              for key, value in values.items()}
    keys = list(values)
    fig = go.Figure(go.Scatterpolar(r=[values[k] for k in keys], theta=keys, fill="toself",
        line=dict(color="#ffb000", width=4), fillcolor="rgba(255,176,0,.32)",
        marker=dict(size=7, color="#ff5e3a")))
    fig.update_layout(title=label, polar=dict(bgcolor="rgba(15,25,42,.55)",
        radialaxis=dict(visible=True, range=[0,5], gridcolor="#53647d", tickfont=dict(color="#dce7f5")),
        angularaxis=dict(gridcolor="#53647d", tickfont=dict(color="#f2f6ff"))),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="#f2f6ff", margin=dict(l=45,r=45,t=44,b=24), height=320)
    return fig

def fifa_player_explanation(name, player_id=None):
    """Return source-grounded attribute detail and cautious role interpretation."""
    record = fifa_profiles_by_id.get(int(player_id)) if player_id is not None else None
    key = " ".join(str(name).strip().lower().split())
    record = record or fifa_profiles.get(key)
    if not record:
        return None
    labels = {
        "fifa_pace": ("Pace", "A game-rating proxy for acceleration and speed; useful context for running in behind or recovery, not match-tracking speed."),
        "fifa_shooting": ("Shooting", "A broad card rating for shot-related ability; it does not show shot volume, shot quality or finishing in this dataset."),
        "fifa_passing": ("Passing", "A broad technical rating. Pair it with event-based progression and pass completion before judging playmaking."),
        "fifa_dribbling": ("Dribbling", "A broad ball-carrying/control rating; it does not establish how often the player beats an opponent in matches."),
        "fifa_defending": ("Defending", "A broad defensive card rating, not a direct measure of tackles, interceptions or defensive positioning in Wyscout."),
        "fifa_physical": ("Physical", "A broad physicality rating; it is not a fitness, endurance or injury-risk measurement."),
        "fifa_composure": ("Composure", "EA's game attribute, not a psychological assessment or validated measure of performance under pressure."),
        "fifa_vision": ("Vision", "A game-rating proxy for awareness and passing vision; actual creative output needs event evidence."),
        "fifa_reactions": ("Reactions", "A game attribute for responsiveness; it should not be presented as measured reaction time."),
        "fifa_ball_control": ("Ball control", "A game rating for receiving and controlling the ball; event data is needed to assess retention under pressure."),
        "fifa_short_passing": ("Short passing", "A game rating for short-pass execution; it does not reveal the player's actual pass success rate."),
        "fifa_finishing": ("Finishing", "A game rating for finishing ability; actual goal conversion requires shots and goals with a suitable sample."),
        "fifa_aggression": ("Aggression", "A game attribute associated with defensive intensity; it is not a behavioural or disciplinary judgement."),
        "fifa_stamina": ("Stamina", "A game rating for endurance, not measured running output or current match fitness."),
        "fifa_strength": ("Strength", "A game rating for physical duels, not a measured duel-win percentage."),
        "fifa_interceptions": ("Interceptions", "A game rating for anticipation; actual interceptions should be counted from match events."),
        "fifa_standing_tackle": ("Standing tackle", "A game rating for standing challenges; actual tackle volume and success are separate measures."),
        "fifa_positioning": ("Positioning", "A game rating for attacking positioning, not a tracking-derived positional measure.")
    }
    rows = []
    for field, (label, explanation) in labels.items():
        value = record.get(field)
        try:
            number = float(value)
            if pd.isna(number):
                continue
        except (TypeError, ValueError):
            continue
        rows.append({"Attribute": label, "FIFA 18 rating": round(number, 1), "What it can and cannot tell us": explanation})
    return pd.DataFrame(rows) if rows else None


def manager_web_figure(profile):
    scores = {dimension: 0.0 for dimension in MANAGER_DIMENSIONS}
    for tag in profile.get("tactical_tags", []):
        dimension = TAG_DIMENSIONS.get(str(tag).lower())
        if dimension:
            scores[dimension] = min(5.0, scores[dimension] + 2.5)
    keys = list(scores)
    fig = go.Figure(go.Scatterpolar(r=[scores[k] for k in keys], theta=keys, fill="toself",
        line_color="#ffb000", fillcolor="rgba(255,176,0,.28)"))
    fig.update_layout(title=f"{profile.get('manager_name','Coach')} · encoded tactical themes",
        polar=dict(radialaxis=dict(visible=True, range=[0,5], gridcolor="#53647d"),
        angularaxis=dict(gridcolor="#34485b")), showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="#eaf0f6", margin=dict(l=35,r=35,t=40,b=20), height=310)
    return fig


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
    # Compact season snapshot from observed match records; no formation is inferred.
    team_matches = team_rows.drop_duplicates("match_id").copy()
    for column in ["team_score", "opponent_score"]:
        team_matches[column] = pd.to_numeric(team_matches[column], errors="coerce")
    scored = team_matches.dropna(subset=["team_score", "opponent_score"])
    if not scored.empty:
        wins = int((scored.team_score > scored.opponent_score).sum())
        draws = int((scored.team_score == scored.opponent_score).sum())
        losses = int((scored.team_score < scored.opponent_score).sum())
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Matches", f"{len(scored)}")
        k2.metric("W – D – L", f"{wins} – {draws} – {losses}")
        k3.metric("Goals scored / match", f"{scored.team_score.mean():.2f}")
        k4.metric("Goals conceded / match", f"{scored.opponent_score.mean():.2f}")
        st.caption("Descriptive results from the available Wyscout match sample; not a tactical or formation rating.")
    else:
        st.info("Match score data is unavailable for this team in the local coach-appearance file.")
    reference = next((x for x in manager_data.get("profiles",[]) if x.get("team_name","").lower() == selected_team.lower()), None)
    if reference:
        manager_name = reference.get("manager_name", "Unverified coach identity")
        flag_data = MANAGER_STYLE_REFERENCES.get(manager_name.lower(), {})
        flag = " !" if flag_data.get("impact_flag") else ""
        st.markdown(f"**Coach profile{flag}: {manager_name} · {reference.get('season', 'season not specified')}**")
        st.write(reference.get("qualitative_summary", "No written tactical summary is available."))
        st.plotly_chart(manager_web_figure(reference), width="stretch", config={"displayModeBar":False})
        st.caption(f"Evidence: {reference.get('evidence_type','not specified')} · confidence: {reference.get('confidence','not rated')}. Web dimensions are encoded from documented tactical tags, not measured match-by-match scores.")
        if flag_data.get("impact_flag"):
            st.caption("! " + flag_data["flag_reason"])
        st.caption("The season reference is not automatically matched to the coach IDs above.")
    else:
        pass
else:
    st.caption("Select a team to inspect the recorded coach IDs and any available curated strategy reference.")


if player_a == player_b:
    st.warning("Choose two different players to make the comparison meaningful.")

run = st.button("ANALYSE MATCH CONTEXT  →", type="primary", width="stretch", disabled=(player_a == player_b))
if run:
    model = joblib.load(MODEL)
    probs = predict_match_state(
        model, minute=minute, team_score=team_score, opponent_score=opponent_score,
        team_side=team_side, score_state=state,
    )
    st.markdown('<div class="section-label">04 / MODEL OUTPUT</div>', unsafe_allow_html=True)
    st.markdown("### Estimated outcome probabilities")
    st.markdown('<div class="note">These estimates describe the match context only. The baseline model uses minute, score, score difference and home/away status. It does <b>not</b> use player identity, position, role, fitness or manager data. Therefore, the probabilities are the same for both options and do not identify a better replacement.</div>', unsafe_allow_html=True)
    metrics = st.columns(3)
    for col, outcome in zip(metrics, ["positive", "neutral", "negative"]):
        col.metric(f"{outcome.title()} outcome", f"{probs.get(outcome, 0):.1%}")
    chart = pd.DataFrame({"Estimated probability": [probs.get(k, 0) for k in ["positive", "neutral", "negative"]]}, index=["Positive", "Neutral", "Negative"])
    st.bar_chart(chart, width="stretch")
    st.markdown('<div class="section-label">05 / PLAYER PROFILES</div>', unsafe_allow_html=True)
    st.caption("FIFA 18 card ratings are mapped to broad tactical dimensions where a conservative Wyscout name match exists. Otherwise a named qualitative reference or position proxy is shown. Card ratings are game data, not real-world event measurements.")
    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"**OPTION A · {name_a}**")
        ref_a = named_player_reference(name_a)
        st.markdown(f"**{name_a}{' !' if ref_a and ref_a.get('impact_flag') else ''}**")
        st.plotly_chart(player_web_figure(pos_a, name_a, player_a), width="stretch", config={"displayModeBar":False})
        detail_a = fifa_player_explanation(name_a, player_a)
        if detail_a is not None:
            st.markdown("**FIFA 18 attribute snapshot · Option A**")
            preferred = ["Pace", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]
            snapshot = detail_a[detail_a["Attribute"].isin(preferred)].set_index("Attribute")["FIFA 18 rating"]
            stat_cols = st.columns(3)
            for stat_col, stat_name in zip(stat_cols, preferred):
                if stat_name in snapshot.index:
                    stat_col.metric(stat_name, f"{snapshot[stat_name]:.0f}/100")
            with st.expander("View all available attributes and definitions"):
                st.dataframe(detail_a[["Attribute", "FIFA 18 rating"]], hide_index=True, width="stretch")
                st.caption("These are FIFA 18 game ratings, not measured match performance.")
        if ref_a:
            st.write(ref_a["summary"])
            st.caption(ref_a["source_note"])
            if ref_a.get("impact_flag"): st.caption("! " + ref_a["flag_reason"])
        else:
            pass
    with cb:
        st.markdown(f"**OPTION B · {name_b}**")
        ref_b = named_player_reference(name_b)
        st.markdown(f"**{name_b}{' !' if ref_b and ref_b.get('impact_flag') else ''}**")
        st.plotly_chart(player_web_figure(pos_b, name_b, player_b), width="stretch", config={"displayModeBar":False})
        detail_b = fifa_player_explanation(name_b, player_b)
        if detail_b is not None:
            st.markdown("**FIFA 18 attribute snapshot · Option B**")
            preferred = ["Pace", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]
            snapshot = detail_b[detail_b["Attribute"].isin(preferred)].set_index("Attribute")["FIFA 18 rating"]
            stat_cols = st.columns(3)
            for stat_col, stat_name in zip(stat_cols, preferred):
                if stat_name in snapshot.index:
                    stat_col.metric(stat_name, f"{snapshot[stat_name]:.0f}/100")
            with st.expander("View all available attributes and definitions"):
                st.dataframe(detail_b[["Attribute", "FIFA 18 rating"]], hide_index=True, width="stretch")
                st.caption("These are FIFA 18 game ratings, not measured match performance.")
        if ref_b:
            st.write(ref_b["summary"])
            st.caption(ref_b["source_note"])
            if ref_b.get("impact_flag"): st.caption("! " + ref_b["flag_reason"])
        else:
            st.caption("No named-player reference yet; this is a positional proxy.")
    st.markdown('<div class="section-label">06 / PLAUSIBLE MATCH EFFECT</div>', unsafe_allow_html=True)
    ea, eb = st.columns(2)
    for col, label, position, player_name, player_id in [
        (ea, "OPTION A", pos_a, name_a, player_a),
        (eb, "OPTION B", pos_b, name_b, player_b),
    ]:
        heading, tradeoff, _ = plausible_effect(position, state, minute, player_name, player_id)
        with col:
            st.markdown(f'<div class="panel"><div class="panel-kicker">{label} · PLAYER ROLE</div><div class="panel-title">{heading}</div><div class="panel-sub">{tradeoff}</div></div>', unsafe_allow_html=True)
    # Comparison summaries are shown without process notes.

st.divider()
st.markdown('<div class="eyebrow">KICK-OFF / MODEL NOTES</div>', unsafe_allow_html=True)
st.caption("Historical associations are not causal effects or guarantees. Outcome labels are provisional pending further validation. Built as an educational decision-support research prototype.")
