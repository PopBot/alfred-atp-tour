#!/usr/bin/env python3
"""
utils.py — Shared utilities for the ATP Tour (atp) Alfred workflow.
Bundled lib/ is loaded first so requests always works regardless of
which Python version Alfred uses on the Mac.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime

# ── Bundled dependencies ──────────────────────────────────────────────────────
WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(WORKFLOW_DIR, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import requests
from image_utils import decode_png_rgba, encode_rgba_png, make_matchup_icon, resize_nearest

# ── Paths ─────────────────────────────────────────────────────────────────────
DEFAULT_ALFRED_CACHE = os.path.expanduser(
    "~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/com.popbot.alfred-atp-tour"
)
CACHE_DIR = os.environ.get("alfred_workflow_cache") or DEFAULT_ALFRED_CACHE
FLAGS_DIR = os.path.join(WORKFLOW_DIR, "flags")
HEADSHOTS_DIR = os.path.join(CACHE_DIR, "headshots")
MATCHUPS_DIR = os.path.join(CACHE_DIR, "matchups")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(FLAGS_DIR, exist_ok=True)
os.makedirs(HEADSHOTS_DIR, exist_ok=True)
os.makedirs(MATCHUPS_DIR, exist_ok=True)

# ── HTTP Session ──────────────────────────────────────────────────────────────
_session = requests.Session()
_session.headers.clear()
_session.headers.update({
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
})


def api_get(url: str, params: dict | None = None, timeout: int = 6, headers: dict | None = None) -> dict | list:
    r = _session.get(url, params=params, timeout=timeout, headers=headers)
    r.raise_for_status()
    return r.json()


# ── IOC / Country Code to ISO-2 & Emoji Flag ──────────────────────────────────
IOC_TO_ISO2: dict[str, str] = {
    "ALG": "DZ", "AND": "AD", "ARG": "AR", "ARM": "AM", "AUS": "AU", "AUT": "AT",
    "AZE": "AZ", "BAH": "BS", "BAR": "BB", "BDI": "BI", "BEL": "BE", "BEN": "BJ",
    "BER": "BM", "BIH": "BA", "BLR": "BY", "BOL": "BO", "BRA": "BR", "BRN": "BH",
    "BUL": "BG", "BUR": "BF", "CAM": "KH", "CAN": "CA", "CAY": "KY", "CHI": "CL",
    "CHN": "CN", "CIV": "CI", "CMR": "CM", "COD": "CD", "COL": "CO", "CRC": "CR",
    "CRO": "HR", "CUB": "CU", "CYP": "CY", "CZE": "CZ", "DEN": "DK", "DOM": "DO",
    "ECU": "EC", "EGY": "EG", "ESA": "SV", "ESP": "ES", "EST": "EE", "ETH": "ET",
    "FIJ": "FJ", "FIN": "FI", "FRA": "FR", "GAB": "GA", "GBR": "GB", "GEO": "GE",
    "GER": "DE", "GHA": "GH", "GRE": "GR", "GUA": "GT", "HAI": "HT", "HKG": "HK",
    "HON": "HN", "HUN": "HU", "INA": "ID", "IND": "IN", "IRI": "IR", "IRL": "IE",
    "IRQ": "IQ", "ISL": "IS", "ISR": "IL", "ISV": "VI", "ITA": "IT", "JAM": "JM",
    "JOR": "JO", "JPN": "JP", "KAZ": "KZ", "KEN": "KE", "KGZ": "KG", "KOR": "KR",
    "KSA": "SA", "KUW": "KW", "LAO": "LA", "LAT": "LV", "LBA": "LY", "LBN": "LB",
    "LIB": "LB", "LIE": "LI", "LTU": "LT", "LUX": "LU", "MAD": "MG", "MAR": "MA",
    "MAS": "MY", "MDA": "MD", "MEX": "MX", "MGL": "MN", "MKD": "MK", "MLI": "ML",
    "MLT": "MT", "MNE": "ME", "MON": "MC", "MOZ": "MZ", "MRI": "MU", "NAM": "NA",
    "NED": "NL", "NEP": "NP", "NGR": "NG", "NCA": "NI", "NOR": "NO", "NZL": "NZ",
    "OMA": "OM", "PAK": "PK", "PAN": "PA", "PAR": "PY", "PER": "PE", "PHI": "PH",
    "PLE": "PS", "POL": "PL", "POR": "PT", "PUR": "PR", "QAT": "QA", "ROU": "RO",
    "ROM": "RO", "RSA": "ZA", "RUS": "RU", "RWA": "RW", "SAM": "WS", "SEN": "SN",
    "SRB": "RS", "SER": "RS", "SGP": "SG", "SIN": "SG", "SLE": "SL", "SLO": "SI",
    "SMR": "SM", "SOL": "SB", "SOM": "SO", "SRI": "LK", "SUD": "SD", "SUI": "CH",
    "SUR": "SR", "SVK": "SK", "SWE": "SE", "SYR": "SY", "TAN": "TZ", "THA": "TH",
    "TJK": "TJ", "TKM": "TM", "TOG": "TG", "TPE": "TW", "TPO": "TW", "TTO": "TT",
    "TUN": "TN", "TUR": "TR", "UAE": "AE", "UGA": "UG", "UKR": "UA", "URU": "UY",
    "USA": "US", "UZB": "UZ", "VAN": "VU", "VEN": "VE", "VIE": "VN", "ZAM": "ZM",
    "ZIM": "ZW",
}


def ioc_to_flag_emoji(ioc: str | None) -> str:
    """Convert 3-letter IOC code (e.g. 'ESP', 'ITA', 'USA') or 2-letter ISO code to flag emoji."""
    if not ioc:
        return "🎾"
    code = ioc.strip().upper()
    iso2 = code if len(code) == 2 else IOC_TO_ISO2.get(code, "")
    if len(iso2) == 2 and iso2.isalpha():
        return chr(0x1F1E6 + ord(iso2[0]) - ord("A")) + chr(0x1F1E6 + ord(iso2[1]) - ord("A"))
    return "🎾"


def extract_ioc_from_flag_url(flag_url: str | None) -> str:
    """Extract 3-letter IOC code from ESPN flag URL like '.../countries/500/esp.png'."""
    if not flag_url:
        return ""
    m = re.search(r"/countries/\d+/([a-zA-Z0-9]+)\.png", flag_url)
    return m.group(1).upper() if m else ""


def _save_64x64_png_bytes(raw_bytes: bytes, out_path: str) -> bool:
    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw_bytes)
        decoded = decode_png_rgba(tmp_path)
        if not decoded:
            return False
        w, h, px = decoded
        if (w, h) != (64, 64):
            px = resize_nearest(px, w, h, 64, 64)
        with open(out_path, "wb") as f:
            f.write(encode_rgba_png(px, 64, 64))
        return True
    except Exception:
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def flag_logo_path(ioc_or_url: str | None) -> str:
    """Return local path to 64x64 country flag PNG, downloading on-demand if missing."""
    default_icon = os.path.join(WORKFLOW_DIR, "icon.png")
    if not ioc_or_url:
        return default_icon

    s = str(ioc_or_url).strip()
    if s.startswith("http"):
        ioc = extract_ioc_from_flag_url(s).lower()
        url = s
    else:
        ioc = s.lower()
        url = f"https://a.espncdn.com/i/teamlogos/countries/500/{ioc}.png"

    if not ioc:
        return default_icon

    bundled = os.path.join(FLAGS_DIR, f"{ioc}.png")
    if os.path.exists(bundled) and os.path.getsize(bundled) > 100:
        return bundled

    cached = os.path.join(CACHE_DIR, f"flag_{ioc}.png")
    if os.path.exists(cached) and os.path.getsize(cached) > 100:
        return cached

    try:
        resp = _session.get(url, timeout=4)
        if resp.status_code == 200 and resp.content:
            if _save_64x64_png_bytes(resp.content, cached):
                return cached
    except Exception:
        pass

    return default_icon


def matchup_flag_icon_path(ioc1: str | None, ioc2: str | None) -> str:
    """Return a 64x64 composite dual-flag PNG for a matchup between ioc1 and ioc2."""
    c1 = (extract_ioc_from_flag_url(ioc1) if (ioc1 and ioc1.startswith("http")) else (ioc1 or "")).strip().lower()
    c2 = (extract_ioc_from_flag_url(ioc2) if (ioc2 and ioc2.startswith("http")) else (ioc2 or "")).strip().lower()

    if not c1 and not c2:
        return os.path.join(WORKFLOW_DIR, "icon.png")
    if not c1:
        return flag_logo_path(c2)
    if not c2:
        return flag_logo_path(c1)

    out_path = os.path.join(MATCHUPS_DIR, f"matchup_{c1}_{c2}.png")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return out_path

    f1 = flag_logo_path(c1)
    f2 = flag_logo_path(c2)
    if make_matchup_icon(f1, f2, out_path):
        return out_path
    return f1


def player_headshot_path(athlete_id: str | int, direct_url: str | None = None, fallback_ioc: str | None = None) -> str:
    """Download & cache player headshot (7-day TTL), falling back to country flag or workflow icon."""
    aid = str(athlete_id).strip()
    if not aid:
        return flag_logo_path(fallback_ioc)

    path = os.path.join(HEADSHOTS_DIR, f"{aid}.png")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path) < 604800) and os.path.getsize(path) > 200:
        return path

    url = direct_url or f"https://a.espncdn.com/i/headshots/tennis/players/full/{aid}.png"
    try:
        resp = _session.get(url, timeout=3)
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(path, "wb") as f:
                f.write(resp.content)
            return path
    except Exception:
        pass

    return flag_logo_path(fallback_ioc)


# ── Tennis Formatting Helpers ─────────────────────────────────────────────────
def sanitize_espn_url(url: str | None, fallback_id: str | None = None, slug: str | None = None) -> str:
    """Fix ESPN's '/null/player/' bug in tennis rankings/athlete links."""
    if url:
        fixed = url.replace("espn.com/null/player/", "espn.com/tennis/player/")
        if "/null/" not in fixed:
            return fixed
    if fallback_id:
        base = f"https://www.espn.com/tennis/player/_/id/{fallback_id}"
        return f"{base}/{slug}" if slug else base
    return "https://www.espn.com/tennis/"


def format_seed(comp_or_rank: dict | int | str | None) -> str:
    """Format tournament seed in brackets '[2] ' if 1..32, else empty string."""
    val = comp_or_rank
    if isinstance(comp_or_rank, dict):
        val = comp_or_rank.get("curatedRank", {}).get("current")
    try:
        s = int(val)
        if 1 <= s <= 32:
            return f"[{s}] "
    except (ValueError, TypeError):
        pass
    return ""


def format_set_linescores(c1_lines: list[dict] | None, c2_lines: list[dict] | None) -> str:
    """
    Format set scores from two competitors' linescores arrays into standard tennis
    notation: '6-4, 7-6(5), 6-3' (showing losing tiebreak score in parentheses).
    """
    if not c1_lines or not c2_lines:
        return ""
    sets = []
    n = min(len(c1_lines), len(c2_lines))
    for i in range(n):
        s1 = c1_lines[i]
        s2 = c2_lines[i]
        v1 = s1.get("value")
        v2 = s2.get("value")
        if v1 is None or v2 is None:
            continue
        g1 = int(float(v1))
        g2 = int(float(v2))
        if g1 == 0 and g2 == 0 and i > 0 and i == n - 1:
            continue
        tb1 = s1.get("tiebreak")
        tb2 = s2.get("tiebreak")
        if tb1 is not None or tb2 is not None:
            # Show the loser's tiebreak points in parentheses if both exist, or whichever is smaller
            if tb1 is not None and tb2 is not None:
                tb_val = min(int(tb1), int(tb2))
            else:
                tb_val = int(tb1 if tb1 is not None else tb2)
            sets.append(f"{g1}-{g2}({tb_val})")
        else:
            sets.append(f"{g1}-{g2}")
    return ", ".join(sets)


# ── File Cache ────────────────────────────────────────────────────────────────
def cache_get(key: str, ttl: int):
    """Return cached data only if younger than ttl seconds, else None."""
    safe_key = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)
    path = os.path.join(CACHE_DIR, f"{safe_key}.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def cache_get_stale(key: str):
    """Return cached data regardless of age (stale-while-revalidate). None if missing."""
    safe_key = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)
    path = os.path.join(CACHE_DIR, f"{safe_key}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def cache_set(key: str, data) -> None:
    safe_key = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)
    path = os.path.join(CACHE_DIR, f"{safe_key}.json")
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ── Timezone ──────────────────────────────────────────────────────────────────
def utc_to_local_datetime(utc_str: str) -> datetime:
    """Convert '2026-11-08T14:00Z' to local datetime."""
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    return dt.astimezone()


def utc_to_local(utc_str: str, include_date: bool = False) -> str:
    """Format local time like 'Sun 9:00 AM' or 'Today 9:00 AM'."""
    try:
        local = utc_to_local_datetime(utc_str)
        now = datetime.now().astimezone()
        if local.date() == now.date():
            day_str = "Today"
        elif include_date:
            day_str = local.strftime("%a %b %-d,")
        else:
            day_str = local.strftime("%a")
        return f"{day_str} {local.strftime('%-I:%M %p')}"
    except Exception:
        return "TBD"


def utc_to_short_date(utc_str: str) -> str:
    """Format '2026-11-07T16:00Z' as 'Nov 7' in local timezone."""
    try:
        local = utc_to_local_datetime(utc_str)
        return local.strftime("%b %-d")
    except Exception:
        return ""


# ── Alfred Output ─────────────────────────────────────────────────────────────
def alfred_error(message: str, detail: str = "") -> None:
    items = [{
        "title": f"⚠️ {message}",
        "subtitle": detail,
        "valid": False,
        "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
    }]
    print(json.dumps({"items": items}))
    sys.exit(0)


def alfred_output(items: list, rerun: float | None = None) -> None:
    out: dict = {"items": items}
    if rerun:
        out["rerun"] = rerun
    print(json.dumps(out))
