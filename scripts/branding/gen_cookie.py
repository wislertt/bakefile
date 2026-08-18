"""Generate organic-cookie SVG mark: wobbly outline, irregular chip blobs, speckles.

Run: python3 gen_cookie.py (writes bakefile-mark-cookie.svg)
"""

import math
import random
from pathlib import Path

from gen_chips import gen

SEED = 42
CACHE = Path(".cache")
CX = CY = 256.0

DOUGH_STOPS = [
    (0, "#DDb283"),
    (55, "#D2A06B"),
    (100, "#BA824A"),
]
CHIP_COLOR = "#7E5232"
GLYPH_COLOR = "#2F1B0C"
GLYPH_STROKE_WIDTH = 43
CRESCENT_DARK = "#5C3616"
SPECKLE_COLOR = "#B98A55"
CRACK_COLOR = "#A9763F"

# glyph scaled 1.2 about (252, 256) from the tuned circle-mark coords; bbox v-center stays 256
GLYPH_PATH = "M156 186.4 L223.2 248.8 L156 313.6"
GLYPH_LINE = ("264", "325.6", "348", "325.6")
GLYPH_SEGMENTS = [
    ((156, 186.4), (223.2, 248.8)),
    ((223.2, 248.8), (156, 313.6)),
    ((264, 325.6), (348, 325.6)),
]
GLYPH_HALF_STROKE = 21.5

# dough layer offset toward top-right light; dark base stays put -> crescent bottom-left
CRESCENT_DX = 9
CRESCENT_DY = -9


def smooth_closed_path(pts):
    """Catmull-Rom through pts -> closed cubic Bezier path string."""
    n = len(pts)
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    d.append("Z")
    return " ".join(d)


def outline_points(rng):
    pts = []
    n = 12
    for i in range(n):
        ang = 2 * math.pi * i / n
        r = 202 + rng.uniform(-4, 10)
        pts.append((CX + r * math.cos(ang), CY + r * math.sin(ang)))
    return pts


def cookie_outline(rng):
    return smooth_closed_path(outline_points(rng))


def outline_bbox(pts):
    """Tight bbox of the smoothed outline: hull of Catmull anchors + bezier controls.

    Cubic bezier lies inside hull of its control points, so this never clips.
    """
    n = len(pts)
    xs, ys = [], []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        xs += [p1[0], p2[0], c1[0], c2[0]]
        ys += [p1[1], p2[1], c1[1], c2[1]]
    return min(xs), min(ys), max(xs), max(ys)


def chip_blob(rng, cx, cy, r):
    pts = []
    n = 8
    for i in range(n):
        ang = 2 * math.pi * i / n
        rr = r * rng.uniform(0.82, 1.14)
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return smooth_closed_path(pts)


def dist_to_seg(px, py, seg):
    (ax, ay), (bx, by) = seg
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def speckles(rng, chips):
    out = []
    tries = 0
    while len(out) < 10 and tries < 4000:
        tries += 1
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(60, 185)
        x, y = CX + rad * math.cos(ang), CY + rad * math.sin(ang)
        r = rng.uniform(1.8, 3.0)
        if any(math.hypot(x - c[0], y - c[1]) < c[2] + r + 5 for c in chips):
            continue
        if any(dist_to_seg(x, y, s) < r + GLYPH_HALF_STROKE + 6 for s in GLYPH_SEGMENTS):
            continue
        out.append((x, y, r))
    return out


def main():
    CACHE.mkdir(exist_ok=True)
    rng = random.Random(SEED)
    chips = gen(SEED)  # tuned scatter, glyph clearance already verified
    outline_pts = outline_points(rng)
    outline = smooth_closed_path(outline_pts)
    chip_paths = [chip_blob(rng, x, y, r) for x, y, r in chips]
    spk = speckles(rng, chips)

    x0, y0, x1, y1 = outline_bbox(outline_pts)
    # dough overhangs the outline by the crescent offset; bbox must cover both layers
    ux0, ux1 = min(x0, x0 + CRESCENT_DX), max(x1, x1 + CRESCENT_DX)
    uy0, uy1 = min(y0, y0 + CRESCENT_DY), max(y1, y1 + CRESCENT_DY)
    pad = 2.0  # keep wobble lobes off the edge, tangency reads as clipping
    vx0, vy0 = math.floor(ux0 - pad), math.floor(uy0 - pad)
    vx1, vy1 = math.ceil(ux1 + pad), math.ceil(uy1 + pad)
    vb = f"{vx0} {vy0} {vx1 - vx0} {vy1 - vy0}"
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="'
        + vb
        + '" role="img" aria-label="bakefile logo">',
        "  <defs>",
        '    <radialGradient id="dough" cx="0.42" cy="0.38" r="0.72">',
    ]
    for off, color in DOUGH_STOPS:
        lines.append(f'      <stop offset="{off}%" stop-color="{color.upper()}"/>')
    lines += [
        "    </radialGradient>",
        '    <radialGradient id="rim" cx="0.62" cy="0.32" r="0.85">',
        '      <stop offset="42%" stop-color="#6B3E1C" stop-opacity="0"/>',
        '      <stop offset="100%" stop-color="#6B3E1C" stop-opacity="0.62"/>',
        "    </radialGradient>",
        '    <clipPath id="cookieClip"><path d="' + outline + '"/></clipPath>',
        "  </defs>",
        "  <!-- cookie: dark base, dough shifted up-right -> sharp crescent bottom-left -->",
        f'  <path d="{outline}" fill="{CRESCENT_DARK}" clip-path="url(#cookieClip)"/>',
        '  <g clip-path="url(#cookieClip)" transform="translate('
        + str(CRESCENT_DX)
        + " "
        + str(CRESCENT_DY)
        + ')">',
        f'    <path d="{outline}" fill="url(#dough)"/>',
        f'    <path d="{outline}" fill="url(#rim)"/>',
        "  </g>",
        "  <!-- baked speckles -->",
    ]
    for x, y, r in spk:
        lines.append(
            f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{SPECKLE_COLOR}" opacity="0.55"/>'
        )
    lines.append("  <!-- chocolate chips (irregular blobs, seed 42) -->")
    for p in chip_paths:
        lines.append(f'  <path d="{p}" fill="{CHIP_COLOR}"/>')
    glyph_stroke = f'stroke="{GLYPH_COLOR}" stroke-width="{GLYPH_STROKE_WIDTH}"'
    lines += [
        "  <!-- prompt glyph -->",
        f'  <path d="{GLYPH_PATH}" fill="none" {glyph_stroke} '
        'stroke-linecap="round" stroke-linejoin="round"/>',
        f'  <line x1="{GLYPH_LINE[0]}" y1="{GLYPH_LINE[1]}" x2="{GLYPH_LINE[2]}" '
        f'y2="{GLYPH_LINE[3]}" {glyph_stroke} stroke-linecap="round"/>',
        "</svg>",
    ]
    out = CACHE / "bakefile-mark-cookie.svg"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
