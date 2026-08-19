"""Generate OG social card: brand surface bg, lockup, tagline, scattered chip crumbs.

Run: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  uv run --with cairosvg --with pillow --with fonttools python3 gen_og.py
"""

import io
import random
import re
from pathlib import Path

import cairosvg
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from gen_cookie import chip_blob
from gen_wordmark import load
from PIL import Image

CACHE = Path(".cache")

W, H = 1200, 630
TAGLINE = "An OOP task runner. Write tasks once, reuse everywhere."
TAG_FONT = ("fonts/Inter.ttf", {"wght": 500})  # formal counterpoint to Shantell lockup
LOCKUP_W = 700
TAG_W = 640
GAP = 56  # lockup bottom -> tagline cap top
SS = 2  # supersample render, LANCZOS back down for crisp edges
CRUMB_SEED = 4
CRUMBS = 20
# keep crumbs off the lockup + tagline block (x0, y0, x1, y1)
# content bounds x 250-950 y 204-426 + 10px margin; crumb pad (r*1.2) adds the rest
SAFE = (240, 194, 960, 436)

# Brand surfaces: soft blue complement family (see BRAND.md -> Color system).
# surface-dark #152A40 / surface-light #F1F7FC; glow = tinted wash, never pure black/white.
MODES = {
    "dark": {
        "bg": "#152A40",
        "glow": "#1F3552",
        "lockup": "bakefile-lockup-dark.svg",
        "tag_ink": "#C9A876",
        "crumbs": ("#D2A06B", "#BA824A"),  # dough tones, chip brown vanishes on dark bg
        "crumb_alpha": 1.0,  # blend ratio into bg, crumb drawn pre-blended + solid
    },
    "light": {
        "bg": "#F1F7FC",
        "glow": "#FFFFFF",
        "lockup": "bakefile-lockup.svg",
        "tag_ink": "#7E5232",
        "crumbs": ("#7E5232", "#5C3616"),  # chip browns on pale blue
        "crumb_alpha": 1.15,  # browns already carry big contrast on pale blue
    },
}


def lockup_inner(name):
    src = (CACHE / name).read_text()
    vb = re.search(r'viewBox="([-\d. ]+)"', src).group(1)
    vw, vh = float(vb.split()[2]), float(vb.split()[3])
    inner = src[src.index(">") + 1 : src.rindex("</svg>")].rstrip()
    return vb, vw, vh, inner


def text_paths(font, text, size):
    """Glyph outlines at `size`, flat baseline y=0. Returns (path d, bounds)."""
    scale = size / font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    gs = font.getGlyphSet()
    ds = []
    x = 0.0
    bp = BoundsPen(None)
    for ch in text:
        gname = cmap[ord(ch)]
        rp = DecomposingRecordingPen(gs)
        gs[gname].draw(rp)
        t = (scale, 0, 0, -scale, x, 0)
        sp = SVGPathPen(None)
        for op in rp.value:
            getattr(TransformPen(sp, t), op[0])(*op[1])
        ds.append(sp.getCommands())
        for op in rp.value:
            getattr(TransformPen(bp, t), op[0])(*op[1])
        x += hmtx[gname][0] * scale
    return " ".join(ds), bp.bounds


def blend(fg, bg, t):
    """Pre-composited mix of fg over bg at ratio t, as a hex string."""
    f = [int(fg[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a * t + c * (1 - t)):02X}" for a, c in zip(f, b, strict=True))


def crumbs(rng):
    out = []
    tries = 0
    while len(out) < CRUMBS and tries < 500:
        tries += 1
        x, y = rng.uniform(24, W - 24), rng.uniform(24, H - 24)
        r = rng.uniform(8, 18)  # crumb scale, not cookie scale: big + faint reads as jelly
        pad = r * 1.2
        if SAFE[0] - pad < x < SAFE[2] + pad and SAFE[1] - pad < y < SAFE[3] + pad:
            continue
        # no crumb-on-crumb overlap (1.4 covers blob wobble ~1.2r + daylight gap)
        if any((x - px) ** 2 + (y - py) ** 2 < ((r + pr) * 1.4) ** 2 for px, py, pr in out):
            continue
        out.append((x, y, r))
    return out


def build(font, mode):
    m = MODES[mode]
    vb, vw, vh, inner = lockup_inner(m["lockup"])
    lw = LOCKUP_W
    lh = lw * vh / vw

    tag_d, (tx0, ty0, tx1, ty1) = text_paths(font, TAGLINE, 100)
    f = TAG_W / (tx1 - tx0)
    tag_h = f * (ty1 - ty0)  # full ink height: ascender through descender ("y" in Python)

    block_h = lh + GAP + tag_h
    top = (H - block_h) / 2
    lx, ly = (W - lw) / 2, top
    tag_base = top + lh + GAP + f * ty1  # baseline y, ascender top at block bottom
    tag_tx = (W - TAG_W) / 2 - f * tx0

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
        "  <defs>",
        '    <radialGradient id="glow" cx="0.5" cy="0.45" r="0.75">',
        f'      <stop offset="0%" stop-color="{m["glow"]}"/>',
        # plateau: flat bg from 55% out so card edges land exactly on the
        # page surface color (docs hero), glow stays a center-only wash.
        # 55% < top-edge offset (cy 0.45 / r 0.75 = 60%) so the nearest edge
        # lands inside the flat band
        f'      <stop offset="55%" stop-color="{m["bg"]}"/>',
        f'      <stop offset="100%" stop-color="{m["bg"]}"/>',
        "    </radialGradient>",
        "  </defs>",
        f'  <rect width="{W}" height="{H}" fill="url(#glow)"/>',
    ]

    rng = random.Random(CRUMB_SEED)
    for i, (x, y, r) in enumerate(crumbs(rng)):
        t = (0.55 - 0.02 * (r - 8)) * m["crumb_alpha"]  # bigger = fainter
        solid = blend(m["crumbs"][i % len(m["crumbs"])], m["bg"], t)
        lines.append(f'  <path d="{chip_blob(rng, x, y, r)}" fill="{solid}"/>')

    lines += [
        f'  <svg x="{lx:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{lh:.1f}" viewBox="{vb}">',
        inner,
        "  </svg>",
        f'  <g transform="translate({tag_tx:.1f} {tag_base:.1f}) scale({f:.4f})">',
        f'    <path d="{tag_d}" fill="{m["tag_ink"]}"/>',
        "  </g>",
        "</svg>",
    ]
    return "\n".join(lines)


def render(svg, name):
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=W * SS)
    img = Image.open(io.BytesIO(png)).resize((W, H), Image.Resampling.LANCZOS)
    out = CACHE / name
    img.convert("RGB").save(out, optimize=True)
    print(f"wrote {out} ({W}x{H}, {out.stat().st_size // 1024}K)")


def main():
    CACHE.mkdir(exist_ok=True)
    tag_font = load(*TAG_FONT)
    for mode in MODES:
        render(build(tag_font, mode), f"og-card-{mode}.png")


if __name__ == "__main__":
    main()
