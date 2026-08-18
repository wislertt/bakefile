"""Generate lockup: cookie mark left + wordmark right, one SVG (light + dark).

Cookie embeds as nested <svg> scaled by viewBox; text reuses wordmark parts.
Run: uv run --with fonttools python3 gen_lockup.py
"""

import math
import re
from pathlib import Path

from gen_wordmark import CHIP, FONT, INK, INK_DARK, load, wordmark_parts

COOKIE = ".cache/bakefile-mark-cookie.svg"
MARK_TEXT_RATIO = 1.1  # mark height vs text ink height
GAP_MARK_RATIO = 0.25  # gap vs mark height
PAD = 2


def cookie_inner():
    with open(COOKIE) as f:
        src = f.read()
    vb = re.search(r'viewBox="([-\d. ]+)"', src).group(1)
    vw, vh = float(vb.split()[2]), float(vb.split()[3])
    inner = src[src.index(">") + 1 : src.rindex("</svg>")].rstrip()
    return vb, vw, vh, inner


def build(ink):
    font = load(*FONT)
    ds, chip, boxes, chip_box, _scale, xh = wordmark_parts(font)
    tx0 = min(b[0] for b in boxes)
    tx1 = max(b[2] for b in boxes)
    ty0 = min(b[1] for b in boxes)
    ty1 = max(b[3] for b in boxes)
    # blob overshoot margin so wobbly chip never clips
    over = 0.32 * (chip_box[3] - chip_box[1])

    text_h = ty1 - ty0
    mark_h = MARK_TEXT_RATIO * text_h
    gap = GAP_MARK_RATIO * mark_h
    vb, cvw, cvh, inner = cookie_inner()
    mark_w = cvw * mark_h / cvh

    cy = -xh / 2  # optical center: x-height midline, baseline at y=0
    cookie_top = cy - mark_h / 2
    text_dx = mark_w + gap - tx0

    x0 = min(0.0, text_dx + tx0 - over)
    x1 = max(mark_w, text_dx + tx1 + over)
    y0 = min(cookie_top, ty0 - over)
    y1 = max(cookie_top + mark_h, ty1 + over)
    vx0, vy0 = math.floor(x0 - PAD), math.floor(y0 - PAD)
    vx1, vy1 = math.ceil(x1 + PAD), math.ceil(y1 + PAD)
    w, h = vx1 - vx0, vy1 - vy0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx0} {vy0} {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="bakefile logo">\n'
        f'  <svg x="0" y="{cookie_top:.1f}" width="{mark_w:.1f}" '
        f'height="{mark_h:.1f}" viewBox="{vb}">\n'
        f"{inner}\n"
        "  </svg>\n"
        f'  <g transform="translate({text_dx:.1f} 0)">\n'
        f'    <path d="{" ".join(ds)}" fill="{ink}"/>\n'
        f'    <path d="{chip}" fill="{CHIP}"/>\n'
        "  </g>\n"
        "</svg>"
    )


def main():
    for suffix, ink in (("", INK), ("-dark", INK_DARK)):
        svg = build(ink)
        out = Path(f".cache/bakefile-lockup{suffix}.svg")
        out.write_text(svg + "\n")
        print(f"wrote {out} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
