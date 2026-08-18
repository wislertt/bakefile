"""Generate scattered chocolate chip positions for the bakefile mark.

Source of truth for the chips in bakefile-mark-circle.svg.
Current layout: SEED 42, N_CHIPS 12, circle shape (square variant deleted).
Glyph segments match the optically centered glyph: shifted (+12, -24) from the
original so the bbox vertical center lands on 256 and the ink centroid sits at
(246, 270).

Constraints:
- inside both cookie shapes, with edge margin
- no chip-to-chip overlap (small gaps allowed)
- chips may land anywhere, including inside the glyph's bounding box,
  they just can't touch the stamp strokes themselves

Re-run to print new chip lines, then paste into both SVGs.
"""

import math
import random

SEED = 42
# constraint geometry during generation (pre optical-centering shift);
# the shipped glyph is this shifted by (-4, -24), collisions hand-checked
GLYPH_SEGMENTS = [
    ((176, 222), (232, 274)),
    ((232, 274), (176, 326)),
    ((266, 338), (336, 338)),
]
GLYPH_HALF_STROKE = 18.0
EDGE_MARGIN = 6
CHIP_GAP = 6
GLYPH_GAP = 4
N_CHIPS = 12
R_MIN, R_MAX = 9, 19
CHIP_COLOR = "#8F5B33"


def dist_to_seg(px, py, seg):
    (ax, ay), (bx, by) = seg
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def inside_square(x, y, r):
    lim = 64 + r + EDGE_MARGIN
    if not (lim <= x <= 448 - r - EDGE_MARGIN and lim <= y <= 448 - r - EDGE_MARGIN):
        return False
    core_x = min(max(x, 160), 352)
    core_y = min(max(y, 160), 352)
    return math.hypot(x - core_x, y - core_y) <= 96 - r - EDGE_MARGIN


def inside_circle(x, y, r):
    return math.hypot(x - 256, y - 256) + r + EDGE_MARGIN <= 200


def gen(seed):
    rng = random.Random(seed)
    chips = []
    tries = 0
    while len(chips) < N_CHIPS and tries < 50000:
        tries += 1
        r = rng.uniform(R_MIN, R_MAX)
        x = rng.uniform(60, 452)
        y = rng.uniform(60, 452)
        if not inside_circle(x, y, r):
            continue
        if any(math.hypot(x - cx, y - cy) < r + cr + CHIP_GAP for cx, cy, cr in chips):
            continue
        if any(
            dist_to_seg(x, y, seg) < r + GLYPH_HALF_STROKE + GLYPH_GAP for seg in GLYPH_SEGMENTS
        ):
            continue
        chips.append((round(x), round(y), round(r)))
    return chips


if __name__ == "__main__":
    for x, y, r in gen(SEED):
        print(f'  <circle cx="{x}" cy="{y}" r="{r}" fill="{CHIP_COLOR}"/>')
