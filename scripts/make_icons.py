#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère static/icon.icns (macOS) et static/icon.ico (Windows)
à partir de static/logo.svg.
"""
import os
import cairosvg
import icnsutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(ROOT, "static", "logo.svg")
TMP_DIR = os.path.join(ROOT, "scripts", "_icon_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# Tailles nécessaires pour un bon rendu macOS (Retina incluse)
SIZES = [16, 32, 64, 128, 256, 512, 1024]

png_paths = {}
for size in SIZES:
    out_path = os.path.join(TMP_DIR, f"icon_{size}.png")
    cairosvg.svg2png(
        url=SVG_PATH,
        write_to=out_path,
        output_width=size,
        output_height=size,
    )
    png_paths[size] = out_path
    print(f"  PNG {size}x{size} -> {out_path}")

# ── .icns (macOS) ────────────────────────────────────────────────────────────
# Clés icns modernes (PNG) par taille — évite l'ambiguïté de guess()
ICNS_KEYS = {
    16: "icp4",
    32: "icp5",
    64: "ic12",   # 32x32@2x
    128: "ic07",
    256: "ic08",
    512: "ic09",
    1024: "ic10",
}

icns_out = os.path.join(ROOT, "static", "icon.icns")
img = icnsutil.IcnsFile()
for size in SIZES:
    img.add_media(key=ICNS_KEYS[size], file=png_paths[size])
img.write(icns_out)
print(f"\n✔ ICNS écrit : {icns_out}")

# ── .ico (Windows) ───────────────────────────────────────────────────────────
ico_out = os.path.join(ROOT, "static", "icon.ico")
ico_sizes = [16, 32, 48, 64, 128, 256]
base_img = Image.open(png_paths[1024]).convert("RGBA")
base_img.save(
    ico_out,
    format="ICO",
    sizes=[(s, s) for s in ico_sizes],
)
print(f"✔ ICO écrit  : {ico_out}")
