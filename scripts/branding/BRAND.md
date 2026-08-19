# bakefile brand

Source of truth for design decisions: color system, tagline, design constants. Generator tooling lives in [`README.md`](./README.md). Change a value here first, then regenerate.

## Color system

Two hue families, never a third: cookie browns (brand core) + soft blue (complement, hue ~209°). Brown is dark orange on the color wheel, so blue is its true complement. Palette picked 2026-08-18 after research: soft/muted blue is the documented pairing for warm browns (bakery brands Norm, Batchi, Hilltop Hearth all use browns + light blue), saturated corporate blue is the known failure mode.

### Cookie family — fixed, never changes

- `ink #2E1B0C` — ink on light: wordmark, body text on light surfaces
- `cream #DDB283` — ink on dark: wordmark, body text on dark surfaces
- `chip #7E5232` — mid brown: i-dot chip, secondary text on light
- `dough-hi #DDB283` → `dough #D2A06B` → `dough-dark #BA824A` — dough gradient: cookie mark fill
- `crescent #5C3616` — baked edge: cookie mark shading

### Soft blue — complement family

- `surface-light #F1F7FC` — light mode background
- `surface-dark #152A40` — dark mode background
- `glaze #4F8CC8` — accent: links, marks, small technical hits
- `glaze-hi #7AB0DE` — light glaze: interactive text on dark surfaces (6.3:1 on `surface-dark`), docs `colors.light`
- `glaze-lo #3B6FA5` — deep glaze: interactive text on light surfaces where AA is required (4.8:1 on `surface-light`), docs `colors.dark`
- `glow-light #FFFFFF` / `glow-dark #1F3552` — radial glow: card/hero background wash

### Rules

- 60-30-10: ~60% surface, ~30% browns, ~10% blue. Blue is scarce on purpose
- Blue = interactive/technical. Brown = brand and words
- `glaze` is graphics only, ~3.2:1 on `surface-light`, fails the 4.5:1 body-text bar. Text stays `ink`/`chip` on light, `cream` on dark
- Surfaces are tinted near-neutrals, never pure `#000000`/`#FFFFFF`
- Cookie mark renders unchanged on any surface, no variants
- OG card carries no `glaze`. Blue appears only as the card surface. Accent belongs to UI (links, marks), decided 2026-08-18
- OG tagline ink `sand #C9A876` on dark, `chip #7E5232` on light. Crumbs use `dough #D2A06B` / `dough-dark #BA824A` on dark, `chip #7E5232` / `crescent #5C3616` on light

## Tagline

Two versions, one voice. Locked 2026-08-18. Never paraphrase, never add a third.

**Card** (OG card, README subtitle, anywhere the logo appears):

```
An OOP task runner. Write tasks once, reuse everywhere.
```

**Metadata** (`pyproject.toml` description, GitHub About):

```
An OOP task runner. Write tasks once, reuse everywhere. Like a Makefile, but reusable and in Python.
```

Card version stays rival-free (no Makefile up top, see promo-copy rule). Metadata version carries the Makefile keyword for search, at the end where it belongs.

## Design constants

- Wordmark font: Shantell Sans, wght 600, BNCE 75, INFM 50, letter bounce echoes the cookie outline wobble
- Chip dot on `i`: 0.7 x tittle height, wobbly blob (same generator as the cookie chips)
- Lockup: mark height = 1.1 x text ink height, gap = 0.25 x mark height, cookie optically centered on x-height midline
- Raster legibility (vision-checked): 48px crisp, 32px acceptable, ≤24px murky — glyph and chips blur, cookie silhouette still reads

## Asset usage

README logo URLs point at `cdn.jsdelivr.net` (raw GitHub SVGs are blocked in `<img>` on PyPI, see jsdelivr note in project memory).
