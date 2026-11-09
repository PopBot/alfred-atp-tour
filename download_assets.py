#!/usr/bin/env python3
"""
download_assets.py — Ensures the official ATP Tour 500x500 workflow icon (`icon.png`)
and 64x64 PNG country flags (`flags/{ioc}.png`) are downloaded and ready for packaging.
"""
from __future__ import annotations

import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(WORKFLOW_DIR, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import requests
from image_utils import decode_png_rgba, encode_rgba_png, resize_nearest

try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

FLAGS_DIR = os.path.join(WORKFLOW_DIR, "flags")
ICON_PATH = os.path.join(WORKFLOW_DIR, "icon.png")
os.makedirs(FLAGS_DIR, exist_ok=True)

ATP_LOGO_URL = (
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3f/ATP_Tour_logo.svg/"
    "960px-ATP_Tour_logo.svg.png?utm_source=en.wikipedia.org&utm_campaign=imageinfo&utm_content=thumbnail"
)

COMMON_IOC_CODES = [
    "alg", "arg", "arm", "aus", "aut", "bdi", "bel", "bih", "blr", "bol", "bra", "bul",
    "can", "chi", "chn", "col", "cro", "cze", "den", "egy", "esa", "esp", "est", "fin",
    "fra", "gbr", "geo", "ger", "gre", "hkg", "hun", "ina", "ind", "irl", "isr", "ita",
    "jpn", "kaz", "ken", "kor", "lat", "ltu", "mex", "mon", "mar", "ned", "nor", "nzl",
    "par", "per", "phi", "pol", "por", "rom", "rou", "rsa", "rus", "ser", "srb", "slo",
    "sui", "svk", "swe", "tha", "tpe", "tpo", "tun", "tur", "ukr", "uru", "usa", "uzb",
]


def ensure_workflow_icon():
    if os.path.exists(ICON_PATH) and os.path.getsize(ICON_PATH) > 1000:
        return
    if not HAS_PIL:
        return
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    r = requests.get(ATP_LOGO_URL, headers=headers, timeout=10)
    r.raise_for_status()
    logo = Image.open(io.BytesIO(r.content)).convert("RGBA")
    logo.thumbnail((440, 440), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    x = (500 - logo.width) // 2
    y = (500 - logo.height) // 2
    alpha = logo.split()[3]
    halo_alpha = alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2))
    halo = Image.new("RGBA", logo.size, (255, 255, 255, 0))
    halo.putalpha(halo_alpha)
    canvas.paste(halo, (x, y), halo)
    canvas.paste(logo, (x, y), logo)
    canvas.save(ICON_PATH, "PNG")
    print(f"  + Generated official ATP Tour icon: {ICON_PATH}")


def _save_64x64_png(raw_bytes: bytes, out_path: str) -> bool:
    if HAS_PIL:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        img.save(out_path, "PNG")
        return True

    tmp_path = out_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)
    try:
        decoded = decode_png_rgba(tmp_path)
        if not decoded:
            return False
        w, h, px = decoded
        if (w, h) != (64, 64):
            px = resize_nearest(px, w, h, 64, 64)
        with open(out_path, "wb") as f:
            f.write(encode_rgba_png(px, 64, 64))
        return True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _download_flag(ioc: str) -> tuple[str, bool]:
    out_path = os.path.join(FLAGS_DIR, f"{ioc}.png")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        return ioc, True
    url = f"https://a.espncdn.com/i/teamlogos/countries/500/{ioc}.png"
    try:
        r = requests.get(url, headers={"User-Agent": "curl/8.7.1"}, timeout=8)
        if r.status_code == 200 and r.content:
            return ioc, _save_64x64_png(r.content, out_path)
    except Exception:
        pass
    return ioc, False


def download_all_assets():
    ensure_workflow_icon()
    print(f"Ensuring 64x64 PNG country flags for {len(COMMON_IOC_CODES)} nations...")
    ok = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(_download_flag, c) for c in COMMON_IOC_CODES]
        for f in as_completed(futs):
            _, success = f.result()
            if success:
                ok += 1
    print(f"Asset sync complete: {ok}/{len(COMMON_IOC_CODES)} country flags ready.")


if __name__ == "__main__":
    download_all_assets()
