#!/usr/bin/env python3
"""
atp_schedule.py — Alfred keywords: atps [query], atpc [query]
Full-Season ATP Tour & Grand Slam Calendar (via official ATP Tour Calendar JSON):
  - `atps`            → Active Tournaments → Upcoming → Completed
  - `atps slam` / `gs`→ Filter to Grand Slams
  - `atps 1000`       → Filter to ATP Masters 1000 events
  - `atps 500` / `250`→ Filter to ATP 500 or ATP 250 events
  - `atps clay`/`grass`/`hard`/`indoor` → Filter by Surface
  - `atps {month/city/name}` → Filter by Month, City, or Tournament Name
"""
from __future__ import annotations

import os
import re
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    flag_logo_path, ioc_to_flag_emoji, WORKFLOW_DIR,
)

CALENDAR_URL = "https://www.atptour.com/en/-/tournaments/calendar/tour"
CACHE_TTL = 3600  # 1 hour

TIER_LABELS: dict[str, str] = {
    "GS": "Grand Slam",
    "1000": "ATP Masters 1000",
    "500": "ATP 500",
    "250": "ATP 250",
    "WS": "Nitto ATP Finals",
    "NG": "Next Gen ATP Finals",
    "UC": "United Cup",
    "LVR": "Laver Cup",
    "DC": "Davis Cup",
    "OL": "Olympics",
}


def fetch_calendar() -> dict:
    key = "atp_tour_calendar"
    data = cache_get(key, CACHE_TTL)
    if data:
        return data
    stale = cache_get_stale(key)
    try:
        data = api_get(CALENDAR_URL, timeout=8)
        cache_set(key, data)
        return data
    except Exception:
        if stale:
            return stale
        raise


def _extract_ioc_from_atp_flag(flag_url: str | None) -> str:
    """Extract 3-letter country code from '/-/media/images/flags/fra.svg'."""
    if not flag_url:
        return ""
    m = re.search(r"/flags/([a-zA-Z]{3})\.", flag_url)
    return m.group(1).upper() if m else ""


def _matches_calendar_filter(t: dict, month_label: str, q: str) -> bool:
    if not q:
        return True
    ttype = str(t.get("Type", "")).upper()
    tier_label = TIER_LABELS.get(ttype, ttype).lower()
    surface = str(t.get("Surface", "")).lower()
    in_out = "indoor" if str(t.get("IndoorOutdoor", "")).upper() == "I" else "outdoor"

    if q in ("slam", "slams", "gs", "grand slam", "major", "majors"):
        return ttype == "GS"
    if q in ("1000", "masters", "masters 1000", "m1000"):
        return ttype == "1000"
    if q in ("500", "atp 500"):
        return ttype == "500"
    if q in ("250", "atp 250"):
        return ttype == "250"
    if q in ("finals", "nitto", "turin"):
        return ttype in ("WS", "NG") or "finals" in t.get("Name", "").lower()
    if q == "live" or q == "active":
        return bool(t.get("IsLive"))
    if q in ("upcoming", "next", "future"):
        return not t.get("IsPastEvent") and not t.get("IsLive")
    if q in ("past", "completed", "results", "archive"):
        return bool(t.get("IsPastEvent"))

    haystack = " ".join([
        str(t.get("Name", "")),
        str(t.get("Location", "")),
        str(t.get("FormattedDate", "")),
        month_label,
        tier_label,
        surface,
        in_out,
    ]).lower()
    return all(tok in haystack for tok in q.split())


def _build_tournament_item(t: dict) -> dict:
    name = t.get("Name", "ATP Tournament")
    loc = t.get("Location", "")
    fdate = t.get("FormattedDate", "")
    ttype = str(t.get("Type", "")).upper()
    tier_str = TIER_LABELS.get(ttype, f"ATP {ttype}" if ttype else "ATP Tour")

    surface = t.get("Surface", "")
    in_out = "Indoor" if str(t.get("IndoorOutdoor", "")).upper() == "I" else "Outdoor"
    surf_str = f"{surface} ({in_out})" if surface else in_out
    purse = t.get("TotalFinancialCommitment") or t.get("PrizeMoneyDetails", "")
    sgl_draw = t.get("SglDrawSize")
    dbl_draw = t.get("DblDrawSize")
    draw_str = f"Draw: {sgl_draw}S/{dbl_draw}D" if sgl_draw else ""

    ioc = _extract_ioc_from_atp_flag(t.get("CountryFlagUrl"))
    flag_emoji = ioc_to_flag_emoji(ioc)
    icon_path = flag_logo_path(ioc) if ioc else os.path.join(WORKFLOW_DIR, "icon.png")

    is_live = bool(t.get("IsLive"))
    is_past = bool(t.get("IsPastEvent"))
    status_prefix = "🔴 " if is_live else ("✅ " if is_past else "📅 ")

    title = f"{status_prefix}{flag_emoji} {name}  [{tier_str}]   —  {fdate}"
    sub_parts = [s for s in [loc, surf_str, draw_str, f"Purse: {purse}" if purse else ""] if s]

    overview_rel = t.get("ScoresUrl") or t.get("TournamentOverviewUrl") or "/en/tournaments"
    draws_rel = t.get("DrawsUrl") or overview_rel
    sched_rel = t.get("ScheduleUrl") or overview_rel

    def _full_atp_url(rel: str) -> str:
        if not rel:
            return "https://www.atptour.com/en/tournaments"
        return rel if rel.startswith("http") else f"https://www.atptour.com{rel}"

    return {
        "title": title,
        "subtitle": "  ·  ".join(sub_parts),
        "arg": _full_atp_url(overview_rel),
        "icon": {"path": icon_path},
        "mods": {
            "cmd": {
                "subtitle": f"⌘ Open {name} Singles/Doubles Draw on ATP Tour",
                "arg": _full_atp_url(draws_rel),
            },
            "alt": {
                "subtitle": f"⌥ Open {name} Daily Schedule / Results on ATP Tour",
                "arg": _full_atp_url(sched_rel),
            },
        },
    }


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = query.lower()

    try:
        cal = fetch_calendar()
    except Exception as e:
        alfred_error("Could not fetch ATP Tour calendar", str(e))
        return

    active_list: list[dict] = []
    upcoming_list: list[dict] = []
    completed_list: list[dict] = []

    for month_block in cal.get("TournamentDates", []):
        month_label = month_block.get("DisplayDate", "")
        for t in month_block.get("Tournaments", []):
            if not _matches_calendar_filter(t, month_label, q):
                continue
            item = _build_tournament_item(t)
            if t.get("IsLive"):
                active_list.append(item)
            elif not t.get("IsPastEvent"):
                upcoming_list.append(item)
            else:
                completed_list.append(item)

    # Show most recently completed tournaments first
    completed_list.reverse()

    items: list[dict] = []
    if active_list:
        items.append({
            "title": f"── 🔴 Active This Week ({len(active_list)}) ──",
            "subtitle": "Filter: atps slam · atps 1000 · atps 500 · atps clay · atps grass · atps {city/month}",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(active_list)

    if upcoming_list:
        items.append({
            "title": f"── 📅 Upcoming ATP Tournaments ({len(upcoming_list)}) ──",
            "subtitle": "Press Enter for Overview, ⌘ for Draw, ⌥ for Schedule",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(upcoming_list)

    if completed_list:
        items.append({
            "title": f"── ✅ Completed Season Tournaments ({len(completed_list)}) ──",
            "subtitle": "Most recent tournaments listed first",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(completed_list)

    if not items:
        alfred_output([{
            "title": f"No ATP tournaments matching '{query}'",
            "subtitle": "Try: atps slam, atps 1000, atps 500, atps clay, atps grass, atps hard, or a city/month",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    alfred_output(items)


if __name__ == "__main__":
    main()
