#!/usr/bin/env python3
"""
atp_player.py — Alfred keyword: atpp {player}
Unified Player Profile, Season Service/Return Stats & Inline Recent Match Results:
  - Multi-match: Lists matching ATP players with World Rank, 2026 YTD & Career W-L/Titles/Prize,
    `⌘` 2026 Service Stats, and `⌥` 2026 Return Stats.
  - Single-player match:
      Row 1     → Player Overview (Rank, YTD & Career W-L/Titles/Prize, ⌘ Serve Stats, ⌥ Return Stats)
      Rows 2..11→ Last 10 tournament matches inline (Tournament, Round, Opponent & Seed, W/L, Set Score)
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import re
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    extract_ioc_from_flag_url, ioc_to_flag_emoji, matchup_flag_icon_path,
    player_headshot_path, sanitize_espn_url, utc_to_short_date, WORKFLOW_DIR,
)

SEARCH_URL = "https://site.web.api.espn.com/apis/search/v2"
ATP_SEARCH_URL = "https://www.atptour.com/en/-/ajax/playersearch/PlayerUrlSearch"
CACHE_TTL = 600  # 10 minutes


def search_espn_atp_players(query: str) -> list[dict]:
    key = f"atp_espn_search_{query.lower().strip()}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    results = []
    try:
        data = api_get(SEARCH_URL, params={"query": query, "limit": 8, "type": "player"})
        for grp in data.get("results", []):
            for item in grp.get("contents", []):
                if item.get("sport") == "tennis" and item.get("defaultLeagueSlug") == "atp":
                    uid = item.get("uid", "")
                    aid = uid.split("~a:")[-1] if "~a:" in uid else str(item.get("id", ""))
                    results.append({
                        "id": aid,
                        "name": item.get("displayName", ""),
                        "web_url": sanitize_espn_url(item.get("link", {}).get("web"), fallback_id=aid),
                        "headshot_url": item.get("image", {}).get("default"),
                    })
    except Exception:
        pass

    # Also check cached ATP Top 150 rankings for instant exact/substring matches
    ranks_data = cache_get_stale("atp_rankings")
    if ranks_data:
        q_low = query.lower().strip()
        seen_ids = {r["id"] for r in results}
        for entry in ranks_data.get("rankings", [{}])[0].get("ranks", []):
            ath = entry.get("athlete", {})
            aid = str(ath.get("id", ""))
            dn = ath.get("displayName", "")
            if aid and aid not in seen_ids and q_low in dn.lower():
                results.append({
                    "id": aid,
                    "name": dn,
                    "web_url": sanitize_espn_url(None, fallback_id=aid),
                    "headshot_url": ath.get("headshot"),
                    "rank": entry.get("current"),
                    "ioc": ath.get("citizenshipCountry") or extract_ioc_from_flag_url(ath.get("flag")),
                })
                seen_ids.add(aid)

    # If exact match on full name or last name is unique among top results, prioritize it
    q_low = query.lower().strip()
    exact = [
        p for p in results
        if p["name"].lower() == q_low or p["name"].lower().split()[-1] == q_low
    ]
    if len(exact) == 1:
        results = exact

    cache_set(key, results)
    return results


def fetch_atp_official_profile_and_stats(full_name: str) -> dict:
    """
    Search official ATP Tour player index by name to resolve 4-char ATP code (e.g. 's0ag'),
    then fetch `/en/-/www/players/hero/{code}` and `/en/-/www/stats/{code}/{year}/all`.
    """
    key = f"atp_official_stats_{full_name.lower()}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    out: dict = {}
    try:
        last_name = full_name.split()[-1]
        srch = api_get(ATP_SEARCH_URL, params={"searchTerm": last_name}, timeout=5)
        items = srch.get("items", []) if isinstance(srch, dict) else []
        chosen_val = ""
        for it in items:
            k_name = str(it.get("Key", "")).strip().lower()
            if k_name == full_name.lower():
                chosen_val = it.get("Value", "")
                break
        if not chosen_val and items:
            # Fallback to matching first initial + last name
            first_init = full_name[0].lower()
            for it in items:
                k_name = str(it.get("Key", "")).strip().lower()
                if k_name.startswith(first_init) and last_name.lower() in k_name:
                    chosen_val = it.get("Value", "")
                    break
        if not chosen_val and len(items) == 1:
            chosen_val = items[0].get("Value", "")

        m = re.search(r"/players/([^/]+)/([a-zA-Z0-9]{4})/overview", chosen_val)
        if m:
            slug, code = m.group(1), m.group(2).lower()
            out["atp_code"] = code
            out["atp_url"] = f"https://www.atptour.com/en/players/{slug}/{code}/overview"
            out["atp_stats_url"] = f"https://www.atptour.com/en/players/{slug}/{code}/player-stats"

            year = datetime.now().year
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_hero = pool.submit(api_get, f"https://www.atptour.com/en/-/www/players/hero/{code}?v=1", None, 5)
                f_stat = pool.submit(api_get, f"https://www.atptour.com/en/-/www/stats/{code}/{year}/all?v=1", None, 5)
                try:
                    out["hero"] = f_hero.result()
                except Exception:
                    out["hero"] = {}
                try:
                    out["stats"] = f_stat.result()
                except Exception:
                    out["stats"] = {}
    except Exception:
        pass

    cache_set(key, out)
    return out


def fetch_espn_career_and_bio(espn_id: str) -> dict:
    key = f"atp_espn_core_{espn_id}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    info: dict = {}
    try:
        core = api_get(f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/athletes/{espn_id}", timeout=5)
        info["age"] = core.get("age")
        info["hand"] = core.get("hand", {}).get("displayValue", "")
        info["height"] = core.get("displayHeight", "")
        info["birthPlace"] = core.get("birthPlace", {}).get("summary", "")
    except Exception:
        pass

    try:
        st = api_get(f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/athletes/{espn_id}/statistics", timeout=5)
        for cat in st.get("splits", {}).get("categories", []):
            for s in cat.get("stats", []):
                info[s.get("name", "")] = s.get("displayValue")
    except Exception:
        pass

    cache_set(key, info)
    return info


def build_player_overview_item(p: dict) -> dict:
    aid = str(p["id"])
    name = p["name"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_atp = pool.submit(fetch_atp_official_profile_and_stats, name)
        f_espn = pool.submit(fetch_espn_career_and_bio, aid)
        atp_data = f_atp.result()
        espn_data = f_espn.result()

    hero = atp_data.get("hero", {}) or {}
    stats_wrap = (atp_data.get("stats", {}) or {}).get("Stats", {}) or {}
    srv = stats_wrap.get("ServiceRecordStats", {}) or {}
    ret = stats_wrap.get("ReturnRecordStats", {}) or {}

    rank = hero.get("SglRank") or p.get("rank")
    hi_rank = hero.get("SglHiRank")
    ioc = (hero.get("NatlId") or p.get("ioc") or "").upper()
    flag_emoji = ioc_to_flag_emoji(ioc)
    age = hero.get("Age") or espn_data.get("age")
    hand = (hero.get("PlayHand", {}) or {}).get("Description") or espn_data.get("hand", "")
    bh = (hero.get("BackHand", {}) or {}).get("Description", "")
    coach = hero.get("Coach", "")

    ytd_w = hero.get("SglYtdWon")
    ytd_l = hero.get("SglYtdLost")
    ytd_t = hero.get("SglYtdTitles")
    ytd_p = hero.get("SglYtdPrizeFormatted")

    car_w = hero.get("SglCareerWon") or espn_data.get("singlesWon", "—")
    car_l = hero.get("SglCareerLost") or espn_data.get("singlesLost", "—")
    car_t = hero.get("SglCareerTitles") or espn_data.get("singlesTitles", "0")
    car_p = hero.get("CareerPrizeFormatted")
    if not car_p and espn_data.get("prize"):
        try:
            car_p = f"${int(float(espn_data['prize'])):,}"
        except Exception:
            car_p = ""

    rank_prefix = f"#{rank} " if rank else ""
    meta_bits = [b for b in [f"Age {age}" if age else "", hand, f"{bh} BH" if bh else ""] if b]
    meta_str = f"  ({', '.join(meta_bits)})" if meta_bits else ""
    title = f"{rank_prefix}{name}  {flag_emoji} {ioc}{meta_str}".strip()

    sub_parts = []
    if ytd_w is not None and ytd_l is not None:
        ytd_str = f"2026: {ytd_w}-{ytd_l}"
        extras = [x for x in [f"{ytd_t} Titles" if ytd_t is not None else "", ytd_p or ""] if x]
        if extras:
            ytd_str += f" ({' · '.join(extras)})"
        sub_parts.append(ytd_str)

    car_str = f"Career: {car_w}-{car_l}"
    car_extras = [x for x in [f"{car_t} Titles" if car_t is not None else "", car_p or ""] if x]
    if car_extras:
        car_str += f" ({' · '.join(car_extras)})"
    sub_parts.append(car_str)

    if hi_rank:
        sub_parts.append(f"Career High: #{hi_rank}")
    if coach:
        sub_parts.append(f"Coach: {coach}")

    profile_url = atp_data.get("atp_url") or p.get("web_url") or f"https://www.espn.com/tennis/player/_/id/{aid}"
    stats_url = atp_data.get("atp_stats_url") or profile_url

    if srv:
        aces = srv.get("Aces", "—")
        df = srv.get("DoubleFaults", "—")
        fs_pct = srv.get("FirstServePercentage", "—")
        fs_won = srv.get("FirstServePointsWonPercentage", "—")
        ss_won = srv.get("SecondServePointsWonPercentage", "—")
        sg_won = srv.get("ServiceGamesWonPercentage", "—")
        bp_svd = srv.get("BreakPointsSavedPercentage", "—")
        cmd_sub = (
            f"⌘ Serve (2026): {aces} Aces · {df} DF · {fs_pct}% 1st Srv · "
            f"{fs_won}% 1st Won · {ss_won}% 2nd Won · {sg_won}% Srv Gms Won · {bp_svd}% BP Saved"
        )
    else:
        cmd_sub = f"⌘ Open {name}'s Full Statistics Profile"

    if ret:
        r1_won = ret.get("FirstServeReturnPointsWonPercentage", "—")
        r2_won = ret.get("SecondServeReturnPointsWonPercentage", "—")
        rg_won = ret.get("ReturnGamesWonPercentage", "—")
        bp_cnv = ret.get("BreakPointsConvertedPercentage", "—")
        bp_opp = ret.get("BreakPointsOpportunities", "—")
        tp_won = ret.get("TotalPointsWonPercentage", "—")
        alt_sub = (
            f"⌥ Return (2026): {r1_won}% 1st Ret Won · {r2_won}% 2nd Ret Won · "
            f"{rg_won}% Ret Gms Won · {bp_cnv}% BP Conv ({bp_opp} ch) · {tp_won}% Total Pts Won"
        )
    else:
        alt_sub = f"⌥ Open {name}'s Match Results Log"

    icon_path = player_headshot_path(aid, direct_url=p.get("headshot_url"), fallback_ioc=ioc)

    return {
        "title": title,
        "subtitle": "  ·  ".join(sub_parts),
        "arg": profile_url,
        "icon": {"path": icon_path},
        "mods": {
            "cmd": {"subtitle": cmd_sub, "arg": stats_url},
            "alt": {"subtitle": alt_sub, "arg": f"https://www.espn.com/tennis/player/results/_/id/{aid}"},
        },
        "_ioc": ioc,
    }


def _parse_espn_note_match(note_text: str, round_desc: str, event_name: str, date_str: str, player_name: str, player_ioc: str) -> dict | None:
    """
    Parse ESPN competition note like:
      '(1) Alexander Zverev (GER) bt (25) Alejandro Tabilo (CHI) 6-2 7-6 (7-2) 6-2'
    """
    if not note_text or " bt " not in note_text:
        return None
    left, right = note_text.split(" bt ", 1)
    # Extract score at the end of right side
    m_right = re.match(r"^(.*?\([A-Z]{3}\))\s+(.*)$", right.strip())
    if m_right:
        loser_str, score_raw = m_right.group(1).strip(), m_right.group(2).strip()
    else:
        loser_str, score_raw = right.strip(), ""

    winner_str = left.strip()

    def _clean_side(s: str) -> tuple[str, str, str]:
        seed_m = re.match(r"^\((\d+)\)\s*(.*)$", s)
        seed = f"[{seed_m.group(1)}] " if seed_m else ""
        rest = seed_m.group(2) if seed_m else s
        ioc_m = re.search(r"\(([A-Z]{3})\)$", rest)
        ioc = ioc_m.group(1) if ioc_m else ""
        p_name = re.sub(r"\s*\([A-Z]{3}\)$", "", rest).strip()
        return seed, p_name, ioc

    w_seed, w_name, w_ioc = _clean_side(winner_str)
    l_seed, l_name, l_ioc = _clean_side(loser_str)

    # Determine if our searched player won
    p_last = player_name.split()[-1].lower()
    won = p_last in w_name.lower()
    if won:
        opp_seed, opp_name, opp_ioc = l_seed, l_name, l_ioc
    else:
        opp_seed, opp_name, opp_ioc = w_seed, w_name, w_ioc

    wl_badge = "✅ W" if won else "❌ L"
    opp_flag = ioc_to_flag_emoji(opp_ioc)
    short_date = utc_to_short_date(date_str)
    score_clean = re.sub(r"\s+", ", ", score_raw.replace(" (7-", "(").replace(" (6-", "("))

    title = f"{wl_badge}  vs  {opp_flag} {opp_seed}{opp_name}   {score_raw}   —  {event_name} ({round_desc})"
    sub_parts = [s for s in [short_date, event_name, round_desc] if s]
    icon_path = matchup_flag_icon_path(player_ioc or w_ioc, opp_ioc)

    return {
        "title": title,
        "subtitle": "  ·  ".join(sub_parts),
        "arg": "https://www.atptour.com/en/scores/current",
        "icon": {"path": icon_path},
        "_date": date_str,
    }


def fetch_player_recent_matches(espn_id: str, player_name: str, player_ioc: str) -> list[dict]:
    key = f"atp_recent_matches_{espn_id}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    year = datetime.now().year
    url = f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/seasons/{year}/athletes/{espn_id}/eventlog"
    try:
        evlog = api_get(url, timeout=5)
    except Exception:
        return []

    raw_items = [x for x in evlog.get("events", {}).get("items", []) if x.get("played")]
    # Take the first 10 items (ESPN eventlog orders newest tournaments first)
    target_items = raw_items[:10]
    if not target_items:
        return []

    event_name_cache: dict[str, str] = {}

    def _fetch_one_match(entry: dict) -> dict | None:
        comp_ref = entry.get("competition", {}).get("$ref", "").replace("http://", "https://")
        ev_ref = entry.get("event", {}).get("$ref", "").replace("http://", "https://")
        if not comp_ref:
            return None
        comp = api_get(comp_ref, timeout=4)
        ev_name = event_name_cache.get(ev_ref)
        if not ev_name and ev_ref:
            try:
                ev_obj = api_get(ev_ref, timeout=4)
                ev_name = ev_obj.get("name", "ATP Tournament")
                event_name_cache[ev_ref] = ev_name
            except Exception:
                ev_name = "ATP Tournament"
        notes = comp.get("notes", [])
        note_txt = notes[0].get("text", "") if notes else ""
        round_desc = comp.get("round", {}).get("description") or (notes[0].get("type", "").split(" - ")[0] if notes else "Match")
        date_str = comp.get("date", "")
        return _parse_espn_note_match(note_txt, round_desc, ev_name or "ATP Tour", date_str, player_name, player_ioc)

    resolved: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_fetch_one_match, it) for it in target_items]
        for f in as_completed(futs):
            try:
                res = f.result()
                if res:
                    resolved.append(res)
            except Exception:
                pass

    resolved.sort(key=lambda x: x.get("_date", ""), reverse=True)
    for r in resolved:
        r.pop("_date", None)

    cache_set(key, resolved)
    return resolved


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if len(query) < 2:
        alfred_output([{
            "title": "Type an ATP player's name...",
            "subtitle": "e.g. atpp sinner, atpp alcaraz, atpp zverev, atpp shelton, atpp djokovic",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    matched = search_espn_atp_players(query)
    if not matched:
        alfred_output([{
            "title": f"No ATP players found for '{query}'",
            "subtitle": "Try searching by last name (e.g. atpp sinner, atpp alcaraz, atpp fritz)",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    # Single-player Unified View: Row 1 = Overview + Serve/Return Mods, Rows 2..11 = Recent Matches
    if len(matched) == 1:
        p = matched[0]
        overview = build_player_overview_item(p)
        p_ioc = overview.pop("_ioc", "")
        recent = fetch_player_recent_matches(str(p["id"]), p["name"], p_ioc)
        items = [overview]
        if recent:
            items.append({
                "title": f"── 🎾 {p['name']} · Recent {datetime.now().year} Tournament Matches ({len(recent)}) ──",
                "subtitle": "Hold ⌘ on Row 1 for 2026 Service Stats · Hold ⌥ on Row 1 for 2026 Return Stats",
                "valid": False,
                "icon": overview["icon"],
            })
            items.extend(recent)
        alfred_output(items)
        return

    # Multi-player match: fetch top 5 in parallel
    subset = matched[:5]
    built: list[tuple[int, dict]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_map = {pool.submit(build_player_overview_item, p): idx for idx, p in enumerate(subset)}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            try:
                it = fut.result()
                it.pop("_ioc", None)
                built.append((idx, it))
            except Exception:
                pass

    built.sort(key=lambda x: x[0])
    alfred_output([it for _, it in built])


if __name__ == "__main__":
    main()
