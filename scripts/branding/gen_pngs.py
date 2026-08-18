"""Rasterize the cookie mark: favicon set (.ico + .png), apple-touch-icon, avatar PNGs.

Cookie viewBox is 433x415 (not square); icons must be, so render a transparent
square master and center the cookie on it, then downscale.
Run: uv run --with cairosvg --with pillow python3 gen_pngs.py
"""

import io
from pathlib import Path

import cairosvg
from PIL import Image

CACHE = Path(".cache")
SRC = CACHE / "bakefile-mark-cookie.svg"

MASTER = 1024
FAVICON_PNG_SIZES = (16, 32, 48)
ICO_SIZES = (16, 32, 48)
APPLE_TOUCH = 180
AVATAR_SIZES = (256, 512)
APPLE_BG = "#FFFFFF"  # iOS composites black behind alpha, keep opaque


def master_png():
    png = cairosvg.svg2png(url=str(SRC), output_width=MASTER)
    img = Image.open(io.BytesIO(png))
    canvas = Image.new("RGBA", (MASTER, MASTER), (0, 0, 0, 0))
    canvas.paste(img, ((MASTER - img.width) // 2, (MASTER - img.height) // 2), img)
    return canvas


def save(master, size, name, bg=None):
    img = master.resize((size, size), Image.Resampling.LANCZOS)
    if bg:
        flat = Image.new("RGBA", img.size, bg)
        flat.alpha_composite(img)
        img = flat
    out = CACHE / name
    img.save(out)
    print(f"wrote {out} ({size}x{size})")


def main():
    CACHE.mkdir(exist_ok=True)
    master = master_png()

    for s in FAVICON_PNG_SIZES:
        save(master, s, f"favicon-{s}.png")
    save(master, APPLE_TOUCH, "apple-touch-icon.png", bg=APPLE_BG)
    for s in AVATAR_SIZES:
        save(master, s, f"bakefile-mark-cookie-{s}.png")

    ico = CACHE / "favicon.ico"
    master.save(ico, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    print(f"wrote {ico} ({'/'.join(map(str, ICO_SIZES))})")


if __name__ == "__main__":
    main()
