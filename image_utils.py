#!/usr/bin/env python3
"""
image_utils.py
Pure Python PNG decoder + compositor — no Pillow needed.
Used to create side-by-side team logo icons for game score results.
"""
from __future__ import annotations

import os
import struct
import zlib


# ── PNG Decoder ───────────────────────────────────────────────────────────────

def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png_rgba(path: str) -> tuple[int, int, list] | None:
    """
    Decode a PNG file to a flat list of (R, G, B, A) tuples.
    Handles RGB, RGBA, Grayscale, Grayscale+Alpha, and Indexed PNGs.
    Returns (width, height, pixels) or None on error.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None

    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    pos = 8
    width = height = bit_depth = color_type = 0
    palette: list[tuple] = []
    trans: list[int] = []
    idat: list[bytes] = []

    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype  = data[pos + 4 : pos + 8]
        cdata  = data[pos + 8 : pos + 8 + length]
        pos   += 12 + length

        if ctype == b"IHDR":
            width, height = struct.unpack(">II", cdata[:8])
            bit_depth     = cdata[8]
            color_type    = cdata[9]
        elif ctype == b"PLTE":
            palette = [
                (cdata[i], cdata[i + 1], cdata[i + 2], 255)
                for i in range(0, len(cdata), 3)
            ]
        elif ctype == b"tRNS":
            if color_type == 3:  # indexed transparency
                trans = list(cdata)
                for i, a in enumerate(trans):
                    if i < len(palette):
                        palette[i] = palette[i][:3] + (a,)
        elif ctype == b"IDAT":
            idat.append(cdata)
        elif ctype == b"IEND":
            break

    if not idat or width == 0:
        return None

    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error:
        return None

    # Bytes-per-pixel in raw scanline (before filter byte)
    bpp_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    bpp     = bpp_map.get(color_type, 3)
    stride  = width * bpp

    rows: list[bytearray] = []
    prev  = bytearray(stride)
    idx   = 0

    for _ in range(height):
        if idx >= len(raw):
            break
        ftype = raw[idx]
        idx  += 1
        row   = bytearray(raw[idx : idx + stride])
        idx  += stride

        if ftype == 1:   # Sub
            for i in range(bpp, len(row)):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif ftype == 2: # Up
            for i in range(len(row)):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ftype == 3: # Average
            for i in range(len(row)):
                a = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + (a + prev[i]) // 2) & 0xFF
        elif ftype == 4: # Paeth
            for i in range(len(row)):
                a = row[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + _paeth(a, b, c)) & 0xFF

        rows.append(row)
        prev = bytearray(row)

    # Convert each row to RGBA tuples
    pixels: list[tuple] = []
    for row in rows:
        for x in range(width):
            i = x * bpp
            if color_type == 6:    # RGBA
                pixels.append((row[i], row[i+1], row[i+2], row[i+3]))
            elif color_type == 2:  # RGB
                pixels.append((row[i], row[i+1], row[i+2], 255))
            elif color_type == 3:  # Indexed
                v = row[i]
                pixels.append(palette[v] if v < len(palette) else (0, 0, 0, 255))
            elif color_type == 0:  # Grayscale
                pixels.append((row[i], row[i], row[i], 255))
            elif color_type == 4:  # Grayscale + Alpha
                pixels.append((row[i], row[i], row[i], row[i+1]))

    return width, height, pixels


# ── Resize ────────────────────────────────────────────────────────────────────

def resize_nearest(
    pixels: list, src_w: int, src_h: int, dst_w: int, dst_h: int
) -> list:
    """Nearest-neighbour resize — fast, good enough for small logos."""
    out = []
    for y in range(dst_h):
        sy = min(int(y * src_h / dst_h), src_h - 1)
        for x in range(dst_w):
            sx = min(int(x * src_w / dst_w), src_w - 1)
            out.append(pixels[sy * src_w + sx])
    return out


# ── PNG Encoder ───────────────────────────────────────────────────────────────

def encode_rgba_png(pixels: list, width: int, height: int) -> bytes:
    """Encode a flat list of (R,G,B,A) tuples to a PNG bytestring."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA

    raw = bytearray()
    for y in range(height):
        raw.append(0)   # filter: None
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw.extend((r, g, b, a))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


# ── Composite ─────────────────────────────────────────────────────────────────

def make_matchup_icon(
    away_logo: str,
    home_logo: str,
    output_path: str,
    logo_size: int = 32,
    canvas: int = 64,
) -> bool:
    """
    Combine two team logos side by side into a square icon.

    Layout (64×64 canvas, each logo 32×32):
        ┌──────────────────────┐
        │        (8px pad)     │
        │  [away]    [home]    │
        │        (8px pad)     │
        └──────────────────────┘

    Returns True on success, False on any error.
    """
    try:
        away_res = decode_png_rgba(away_logo)
        home_res = decode_png_rgba(home_logo)
        if not away_res or not home_res:
            return False

        aw, ah, away_px = away_res
        hw, hh, home_px = home_res

        if aw != logo_size or ah != logo_size:
            away_px = resize_nearest(away_px, aw, ah, logo_size, logo_size)
        if hw != logo_size or hh != logo_size:
            home_px = resize_nearest(home_px, hw, hh, logo_size, logo_size)

        # Transparent canvas
        out = [(0, 0, 0, 0)] * (canvas * canvas)

        top      = (canvas - logo_size) // 2   # vertical centering offset
        away_col = canvas // 4 - logo_size // 2  # left logo x start  (~0)
        home_col = canvas // 4 * 3 - logo_size // 2  # right logo x start (~32)

        for y in range(logo_size):
            for x in range(logo_size):
                cy = top + y
                # Away logo (left)
                cx_a = away_col + x
                if 0 <= cx_a < canvas and 0 <= cy < canvas:
                    out[cy * canvas + cx_a] = away_px[y * logo_size + x]
                # Home logo (right)
                cx_h = home_col + x
                if 0 <= cx_h < canvas and 0 <= cy < canvas:
                    out[cy * canvas + cx_h] = home_px[y * logo_size + x]

        png_data = encode_rgba_png(out, canvas, canvas)
        with open(output_path, "wb") as f:
            f.write(png_data)
        return True

    except Exception:
        return False
