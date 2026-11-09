#!/usr/bin/env python3
"""
atp_rankings.py — Alfred keyword: atpr [query]
Official PIF ATP Tour Singles Rankings (Top 150 via ESPN API):
  - `atpr`            → Top 50 ATP Singles Players
  - `atpr top10`      → Top 10 ATP Singles Players
  - `atpr top25`      → Top 25 ATP Singles Players
  - `atpr all`        → Full Top 150 ATP Singles Players
  - `atpr usa` / `ita`→ Filter Top 150 by Country (IOC code or country name)
  - `atpr sinner`     → Filter Top 150 by Player Name
"""
from __future__ import annotations

import os
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    extract_ioc_from_flag_url, flag_logo_path, ioc_to_flag_emoji,
    player_headshot_path, sanitize_espn_url, WORKFLOW_DIR,
)

RANKINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings"
CACHE_TTL = 600  # 10 minutes


def fetch_rankings() -> dict:
    key = "atp_rankings"
    data = cache_get(key, CACHE_TTL)
    if data:
        return data
    stale = cache_get_stale(key)
    try:
        data = api_get(RANKINGS_URL)
        cache_set(key, data)
        return data
    except Exception:
        if stale:
            return stale
        raise


def _format_trend(trend: str | None, current: int, previous: int) -> str:
    if previous and previous > 0:
        if previous == current:
            return "—"
        diff = previous - current
        return f"▲{diff}" if diff > 0 else f"▼{abs(diff)}"
    if trend and trend not in ("-", ""):
        if trend.startswith("+"):
            return f"▲{trend[1:]}"
        if trend.startswith("-"):
            return f"▼{trend[1:]}"
        return trend
    return "—"


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = query.lower()

    try:
        data = fetch_rankings()
    except Exception as e:
        alfred_error("Could not fetch PIF ATP Rankings", str(e))
        return

    rankings_list = data.get("rankings", [])
    if not rankings_list or not rankings_list[0].get("ranks"):
        alfred_error("ATP Rankings data unavailable", "Please try again shortly.")
        return

    poll = rankings_list[0]
    ranks = poll.get("ranks", [])

    # Determine slice limit or search filter
    limit = 50
    filter_term = ""
    if q in ("top10", "10"):
        limit = 10
    elif q in ("top20", "20"):
        limit = 20
    elif q in ("top25", "25"):
        limit = 25
    elif q in ("top50", "50", ""):
        limit = 50
    elif q in ("all", "top100", "100", "top150", "150"):
        limit = 150
    else:
        filter_term = q
        limit = 150

    filtered_entries = []
    for entry in ranks:
        if not filter_term:
            filtered_entries.append(entry)
            continue
        ath = entry.get("athlete", {})
        name = ath.get("displayName", "").lower()
        ioc = (ath.get("citizenshipCountry") or extract_ioc_from_flag_url(ath.get("flag"))).lower()
        country_name = ath.get("flagAltText", "").lower()
        birth = ath.get("birthPlace", {}).get("summary", "").lower()

        # Exact IOC code match or substring match in name/country
        if filter_term == ioc or filter_term in name or filter_term in country_name or filter_term in birth:
            filtered_entries.append(entry)

    filtered_entries = filtered_entries[:limit]
    if not filtered_entries:
        alfred_output([{
            "title": f"No ranked ATP players matching '{query}'",
            "subtitle": "Try: atpr top10, atpr all, atpr usa, atpr ita, or use atpp {player} for full player search",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    header_label = f"PIF ATP Singles Rankings (Filtered: '{query}')" if filter_term else f"PIF ATP Singles Rankings (Top {len(filtered_entries)})"
    items = [{
        "title": f"── 🏆 {header_label} ──",
        "subtitle": "Filter by country (atpr usa, atpr ita), slice (atpr top10, atpr all), or player name",
        "valid": False,
        "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
    }]

    for idx, entry in enumerate(filtered_entries):
        curr = int(entry.get("current", 0))
        prev = int(entry.get("previous", 0))
        pts = int(float(entry.get("points", 0)))
        trend_str = _format_trend(entry.get("trend"), curr, prev)

        ath = entry.get("athlete", {})
        aid = str(ath.get("id", ""))
        name = ath.get("displayName", "Unknown Player")
        ioc = (ath.get("citizenshipCountry") or extract_ioc_from_flag_url(ath.get("flag"))).upper()
        flag_emoji = ioc_to_flag_emoji(ioc)
        country_full = ath.get("flagAltText", ioc)
        age = ath.get("age")
        birth = ath.get("birthPlace", {}).get("summary", "")

        # Download headshots for top 15 visible items or when filtered; use cached headshot or flag for the rest
        headshot_url = ath.get("headshot")
        if idx < 15 or len(filtered_entries) <= 25:
            icon_path = player_headshot_path(aid, direct_url=headshot_url, fallback_ioc=ioc)
        else:
            cached_hs = os.path.join(os.path.dirname(flag_logo_path(ioc)), "headshots", f"{aid}.png")
            icon_path = cached_hs if os.path.exists(cached_hs) else flag_logo_path(ioc)

        profile_url = ""
        for l in ath.get("links", []):
            if "playercard" in l.get("rel", []):
                profile_url = sanitize_espn_url(l.get("href"), fallback_id=aid)
                break
        if not profile_url:
            profile_url = sanitize_espn_url(None, fallback_id=aid)

        results_url = f"https://www.espn.com/tennis/player/results/_/id/{aid}"

        title = f"#{curr} {name}  {flag_emoji} {ioc}   —  {pts:,} pts  ({trend_str})"
        sub_parts = [f"Prev: #{prev}" if prev else "Prev: —"]
        if age:
            sub_parts.append(f"Age: {age}")
        if birth:
            sub_parts.append(birth)
        elif country_full:
            sub_parts.append(country_full)

        items.append({
            "title": title,
            "subtitle": "  ·  ".join(sub_parts),
            "arg": profile_url,
            "icon": {"path": icon_path},
            "mods": {
                "cmd": {
                    "subtitle": f"⌘ Open {name}'s Season Results & Match Log on ESPN",
                    "arg": results_url,
                },
                "alt": {
                    "subtitle": f"⌥ Tip: Type 'atpp {name.split()[-1].lower()}' for 2026 Serve/Return stats",
                    "arg": profile_url,
                },
            },
        })

    alfred_output(items)


if __name__ == "__main__":
    main()
