#!/usr/bin/env python3
"""
atp_tournament.py — Alfred keyword: atpt [query]
Full Round-by-Round Tournament Draw & Results Viewer:
  - `atpt`            → Active ATP tournament main draw grouped by Round (Final → SF → QF → R16 → R32 → R64)
  - `atpt doubles`    → Active ATP tournament Doubles draw by Round
  - `atpt qual`       → Qualifying draw by Round
  - `atpt {name}`     → Filter to a specific active tournament or round (`atpt paris`, `atpt stockholm`, `atpt sf`)
"""
from __future__ import annotations

import os
import sys

from atp import (
    fetch_atp_live_gateway, fetch_scoreboard, format_match_item, ROUND_ORDER,
)
from utils import alfred_error, alfred_output, WORKFLOW_DIR


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = query.lower()

    try:
        sb = fetch_scoreboard()
    except Exception as e:
        alfred_error("Could not fetch ATP Tournament Draw", str(e))
        return

    live_gw = fetch_atp_live_gateway()
    events = sb.get("events", [])

    want_doubles = "doubles" in q or "dbl" in q
    want_qual = "qual" in q
    tokens = [t for t in q.split() if t not in ("doubles", "dbl", "qual", "qualifying", "draw")]

    items: list[dict] = []

    for ev in events:
        t_name = ev.get("name", "ATP Tournament")
        t_venue = ev.get("venue", {}).get("fullName", "")
        t_url = "https://www.atptour.com/en/scores/current"
        for l in ev.get("links", []):
            if l.get("href") and "/null/" not in l.get("href", ""):
                t_url = l["href"]
                break

        # If user specified a tournament/player filter, check if tournament or any match matches
        for grp in ev.get("groupings", []):
            g_info = grp.get("grouping", {})
            g_slug = g_info.get("slug", "")
            g_label = g_info.get("displayName", "Singles")

            if want_doubles and "doubles" not in g_slug:
                continue
            if not want_doubles and "doubles" in g_slug:
                continue

            comps = grp.get("competitions", [])
            by_round: dict[str, list[dict]] = {}

            for comp in comps:
                round_name = comp.get("round", {}).get("displayName", "Main Draw")
                is_qual = "qualifying" in round_name.lower()
                if is_qual and not want_qual:
                    continue
                if want_qual and not is_qual:
                    continue

                if tokens:
                    haystack = f"{t_name} {t_venue} {round_name}".lower()
                    for c in comp.get("competitors", []):
                        ath = c.get("athlete", {})
                        roster = c.get("roster", {})
                        haystack += " " + ath.get("displayName", "").lower() + " " + roster.get("displayName", "").lower()
                    if not all(tok in haystack for tok in tokens):
                        continue

                try:
                    m_item, _ = format_match_item(comp, t_name, t_url, g_label, live_gw)
                    by_round.setdefault(round_name, []).append(m_item)
                except Exception:
                    continue

            if not by_round:
                continue

            sorted_rounds = sorted(by_round.keys(), key=lambda r: ROUND_ORDER.get(r, 9))
            sub_parts = [s for s in [t_venue, g_label, "Switch: atpt doubles · atpt qual"] if s]
            for r_name in sorted_rounds:
                r_matches = by_round[r_name]
                items.append({
                    "title": f"── 🏆 {t_name} · {r_name} ({len(r_matches)}) ──",
                    "subtitle": " · ".join(sub_parts),
                    "valid": False,
                    "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
                })
                items.extend(r_matches)

    if not items:
        alfred_output([{
            "title": f"No tournament draw matches found for '{query}'",
            "subtitle": "Try: atpt (main draw), atpt doubles, atpt qual, or a tournament/player name",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    alfred_output(items)


if __name__ == "__main__":
    main()
