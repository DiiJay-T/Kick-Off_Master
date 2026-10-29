"""Download and match FIFA 18 Ultimate Team card ratings to Wyscout players.

The source contains card-level ratings (pace, shooting, passing, dribbling,
defending, physical), not the full EA career-mode attribute set. Name matches
are conservative: ambiguous duplicate names are reported, not silently merged
to a specific Wyscout identity.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://raw.githubusercontent.com/kevinheavey/fifa18-even-more-player-data/master/data/final/current/complete.csv"
RAW = Path("data/raw/fifa18_complete.csv")
PLAYERS = Path("data/raw/players.json")
OUT = Path("data/processed")
ATTRIBUTE_ALIASES = {"pace":["pace"],"shooting":["shooting"],"passing":["passing"],"dribbling":["dribbling"],"defending":["defending"],"physical":["physical"],"composure":["composure"],"vision":["vision"],"reactions":["reactions"],"ball_control":["ball_control","ballcontrol"],"short_passing":["short_passing","shortpassing"],"finishing":["finishing"],"aggression":["aggression"],"stamina":["stamina"],"strength":["strength"],"interceptions":["interceptions"],"standing_tackle":["standing_tackle","standingtackle"],"positioning":["positioning"]}


def normalise(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def download() -> None:
    if RAW.exists() and RAW.stat().st_size:
        print(f"Using existing source file: {RAW}")
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(URL, headers={"User-Agent": "KICK-OFF-research/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, RAW.open("wb") as target:
        target.write(response.read())
    print(f"Downloaded {RAW}")


def main() -> None:
    download()
    fifa = pd.read_csv(RAW, low_memory=False)
    columns = {str(col).strip().lower().replace(" ", "_"): col for col in fifa.columns}
    name_col = next((columns[k] for k in ("name", "player_name", "short_name") if k in columns), None)
    club_col = next((columns[k] for k in ("club", "club_name", "team") if k in columns), None)
    position_col = next((columns[k] for k in ("position", "best_position", "player_positions") if k in columns), None)
    id_col = next((columns[k] for k in ("id", "sofifa_id", "player_id") if k in columns), None)
    if name_col is None:
        raise ValueError("FIFA source has no recognised player-name column. Columns: " + str(list(fifa.columns[:30])))
    fifa["name_key"] = fifa[name_col].map(normalise)
    selected = {}
    for target, aliases in ATTRIBUTE_ALIASES.items():
        source = next((columns[a] for a in aliases if a in columns), None)
        if source:
            selected[target] = source
            fifa[source] = pd.to_numeric(fifa[source], errors="coerce")
    if not selected:
        raise ValueError("No recognised FIFA attribute columns found.")
    aggregations = {"fifa_name": (name_col, "first"), "fifa_card_rows": (name_col, "size")}
    if club_col:
        aggregations["fifa_clubs"] = (club_col, lambda x: " | ".join(sorted(set(x.dropna().astype(str))))[:500])
    if position_col:
        aggregations["fifa_positions"] = (position_col, lambda x: " | ".join(sorted(set(x.dropna().astype(str))))[:200])
    for target, source in selected.items():
        aggregations["fifa_" + target] = (source, "median")
    if id_col:
        aggregations["fifa_ids"] = (id_col, lambda x: " | ".join(sorted(set(x.dropna().astype(str))))[:200])
    grouped = fifa.groupby("name_key", dropna=False).agg(**aggregations).reset_index()
    with PLAYERS.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    wyscout_players = payload if isinstance(payload, list) else payload.get("players", [])
    rows = []
    unmatched = []
    wyscout_name_counts = {}
    for player in wyscout_players:
        if isinstance(player, dict):
            display = player.get("shortName") or ""
            full = " ".join(str(player.get(k) or "") for k in ("firstName", "lastName")).strip()
            for alias in {normalise(display), normalise(full)}:
                if alias:
                    wyscout_name_counts[alias] = wyscout_name_counts.get(alias, 0) + 1

    for player in wyscout_players:
        if not isinstance(player, dict):
            continue
        pid = player.get("wyId")
        display = player.get("shortName") or ""
        full = " ".join(str(player.get(k) or "") for k in ("firstName", "lastName")).strip()
        name = full or display
        aliases = list(dict.fromkeys(k for k in (normalise(full), normalise(display)) if k))
        hits = []
        for alias in aliases:
            candidates = grouped[grouped["name_key"] == alias]
            if len(candidates) == 1:
                hits.append((alias, candidates.iloc[0]))
        unique_hits = {str(row["name_key"]): row for _, row in hits}
        if len(unique_hits) == 1 and all(wyscout_name_counts.get(alias, 0) == 1 for alias in aliases if alias in unique_hits):
            row = next(iter(unique_hits.values())).to_dict()
            row.update({
                "wy_id": pid,
                "wyscout_name": name,
                "wyscout_display_name": display,
                "match_status": "exact_full_name" if normalise(full) == row["name_key"] else "exact_display_name"
            })
            rows.append(row)
        elif len(unique_hits) > 1:
            unmatched.append({"wy_id": pid, "wyscout_name": name, "reason": "conflicting_name_aliases"})
        elif any(wyscout_name_counts.get(alias, 0) > 1 for alias in aliases):
            unmatched.append({"wy_id": pid, "wyscout_name": name, "reason": "duplicate_wyscout_name"})
        else:
            unmatched.append({"wy_id": pid, "wyscout_name": name, "reason": "no_fifa_name_match"})

    OUT.mkdir(parents=True, exist_ok=True)
    matched = pd.DataFrame(rows)
    matched.to_csv(OUT / "player_fifa18_profiles.csv", index=False)
    pd.DataFrame(unmatched).to_csv(OUT / "player_fifa18_match_report.csv", index=False)
    print(f"FIFA card rows: {len(fifa):,}")
    print(f"Wyscout player records: {len(wyscout_players):,}")
    print(f"Conservative name matches: {len(matched):,}")
    print(f"Unmatched/ambiguous: {len(unmatched):,}")
    print(f"Saved: {OUT / 'player_fifa18_profiles.csv'}")
    print(f"Saved: {OUT / 'player_fifa18_match_report.csv'}")


if __name__ == "__main__":
    main()
