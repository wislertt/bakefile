"""Generate bakefile wordmark: Shantell Sans outlines -> SVG, chip blob as i-dot.

Run: uv run --with fonttools python3 gen_wordmark.py
"""

import math
import random
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from gen_cookie import chip_blob

TEXT = "bakefile"
SIZE = 160
INK = "#2E1B0C"
INK_DARK = "#DDB283"
CHIP = "#7E5232"
PAD = 4
CACHE = Path(".cache")

FONT = ("fonts/ShantellSans.ttf", {"wght": 600, "BNCE": 75, "INFM": 50})


def load(path, overrides):
    font = TTFont(path)
    if "fvar" in font:
        axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
        axes.update(overrides)
        font = instantiateVariableFont(font, axes, inplace=True)
    return font


def contours_of(glyph_set, gname):
    rp = DecomposingRecordingPen(glyph_set)
    glyph_set[gname].draw(rp)
    conts, cur = [], []
    for op in rp.value:
        cur.append(op)
        if op[0] == "closePath":
            conts.append(cur)
            cur = []
    if cur:
        conts.append(cur)
    return conts


def replay(cont, pen):
    for name, args in cont:
        getattr(pen, name)(*args)


def cont_bounds(cont, transform):
    bp = BoundsPen(None)
    replay(cont, TransformPen(bp, transform))
    return bp.bounds  # (x0, y0, x1, y1) transformed space


def wordmark_parts(font):
    """Return (glyph path cmds, chip path, ink boxes, chip box, scale, x-height)."""
    upem = font["head"].unitsPerEm
    scale = SIZE / upem
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    gs = font.getGlyphSet()

    ds = []
    chip = None
    boxes = []
    chip_box = None
    x = 0.0
    rng = random.Random(7)
    for ch in TEXT:
        gname = cmap[ord(ch)]
        conts = contours_of(gs, gname)
        t = (scale, 0, 0, -scale, x, 0)
        drop = None
        if ch == "i":
            # tittle = topmost contour on screen = min y in svg space (y flipped)
            fb = [cont_bounds(c, t) for c in conts]
            drop = min(range(len(conts)), key=lambda k: fb[k][1])
        for k, cont in enumerate(conts):
            if k == drop:
                tx0, ty0, tx1, ty1 = cont_bounds(cont, t)
                cx, cy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
                r = (ty1 - ty0) * 0.7
                chip = chip_blob(rng, cx, cy, r)
                chip_box = (tx0, ty0, tx1, ty1)
                boxes.append((tx0, ty0, tx1, ty1))
                continue
            sp = SVGPathPen(None)
            replay(cont, TransformPen(sp, t))
            ds.append(sp.getCommands())
            boxes.append(cont_bounds(cont, t))
        x += hmtx[gname][0] * scale
    return ds, chip, boxes, chip_box, scale, font["OS/2"].sxHeight * scale


def build(font, ink):
    ds, chip, boxes, chip_box, _scale, _xh = wordmark_parts(font)
    # blob radius overshoots the tittle box; cover it plus outline wobble
    over = 0.32 * (chip_box[3] - chip_box[1])
    xs0 = min(b[0] for b in boxes)
    ys0 = min(b[1] for b in boxes)
    xs1 = max(b[2] for b in boxes)
    ys1 = max(b[3] for b in boxes)
    vx0, vy0 = math.floor(xs0 - PAD - over), math.floor(ys0 - PAD - over)
    vx1, vy1 = math.ceil(xs1 + PAD + over), math.ceil(ys1 + PAD + over)
    w, h = vx1 - vx0, vy1 - vy0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx0} {vy0} {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="bakefile wordmark">\n'
        f'  <path d="{" ".join(ds)}" fill="{ink}"/>\n'
        f'  <path d="{chip}" fill="{CHIP}"/>\n'
        "</svg>"
    )


def main():
    font = load(*FONT)
    CACHE.mkdir(exist_ok=True)
    for suffix, ink in (("", INK), ("-dark", INK_DARK)):
        svg = build(font, ink)
        out = CACHE / f"bakefile-wordmark{suffix}.svg"
        out.write_text(svg + "\n")
        print(f"wrote {out} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
