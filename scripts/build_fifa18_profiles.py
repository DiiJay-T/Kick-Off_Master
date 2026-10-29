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

URL = "https://raw.githubusercontent.com/kafagy/fifa-FUT-Data/master/FIFA18.csv"
RAW = Path("data/raw/fifa18_ultimate_team.csv")
PLAYERS = Path("data/raw/players.json")
OUT = Path("data/processed")
RATING_COLS = ["PACE", "SHOOTING", "PASSING", "DRIBBLING", "DEFENDING", "PHYSICAL"]


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
    fifa = pd.read_csv(RAW)
    required = {"NAME", "CLUB", "POSITION", *RATING_COLS}
    missing = required - set(fifa.columns)
    if missing:
        raise ValueError(f"FIFA source schema changed; missing columns: {sorted(missing)}")
    for column in RATING_COLS:
        fifa[column] = pd.to_numeric(fifa[column], errors="coerce")
    fifa["name_key"] = fifa["NAME"].map(normalise)

    # Collapse multiple FUT cards/positions for one displayed name using medians.
    # Keep counts and source clubs so the dashboard can disclose aggregation.
    grouped = fifa.groupby("name_key", dropna=False).agg(
        fifa_name=("NAME", "first"),
        fifa_card_rows=("NAME", "size"),
        fifa_clubs=("CLUB", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))[:500]),
        **{f"fifa_{c.lower()}": (c, "median") for c in RATING_COLS},
    ).reset_index()

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
