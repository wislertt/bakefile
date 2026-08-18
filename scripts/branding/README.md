# Branding generators

Tooling that generates the brand assets (cookie mark, wordmark, lockup, favicons, OG card). Design decisions — colors, tagline, constants — live in [`BRAND.md`](./BRAND.md). Outputs are committed to `docs/img/brand/`. Regenerate only when a design constant changes, then copy the files over.

## Files

| File              | Produces                                                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `gen_chips.py`    | chip scatter tuning (seed 42), imported by `gen_cookie.py`                                                                                  |
| `gen_cookie.py`   | `bakefile-mark-cookie.svg`                                                                                                                  |
| `gen_wordmark.py` | `bakefile-wordmark.svg`, `bakefile-wordmark-dark.svg`                                                                                       |
| `gen_lockup.py`   | `bakefile-lockup.svg`, `bakefile-lockup-dark.svg` (reads the generated cookie mark)                                                         |
| `gen_pngs.py`     | `favicon.ico` + `favicon-{16,32,48}.png`, `apple-touch-icon.png` (white bg), `bakefile-mark-cookie-{256,512}.png`                           |
| `gen_og.py`       | `og-card-dark.png`, `og-card-light.png` (1200×630, brand surfaces + lockup + Inter tagline + chip crumbs; GitHub social preview / og:image) |

## Regenerate

Run from this directory. Needs [fonttools](https://fonttools.readthedocs.io) (pulled on the fly by `uv`):

```bash
cd scripts/branding
uv run --with fonttools python3 gen_cookie.py
uv run --with fonttools python3 gen_wordmark.py
uv run --with fonttools python3 gen_lockup.py
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  uv run --with cairosvg --with pillow python3 gen_pngs.py
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  uv run --with cairosvg --with pillow --with fonttools python3 gen_og.py
cp .cache/bakefile-*.svg .cache/favicon* .cache/apple-touch-icon.png \
  .cache/og-card-*.png ../../docs/img/brand/
```

Generated files land in `.cache/` (gitignored). Dependency chain: lockup imports wordmark parts, wordmark imports `chip_blob` from the cookie generator, lockup reads the generated cookie mark, `gen_og.py` reads the generated lockups. Run in the order above.

`gen_pngs.py` and `gen_og.py` need system cairo (`brew install cairo`) — cairosvg has no wheel for it, hence the `DYLD_FALLBACK_LIBRARY_PATH` prefix on macOS.

`preview.html` renders the `.cache/` outputs for side-by-side review. Serve: `python3 -m http.server 8742` from this directory.

## Font license

`fonts/ShantellSans.ttf` is [Shantell Sans](https://fonts.google.com/specimen/Shantell+Sans) by Shantell Martin (digitized by [Arrow Type](https://github.com/arrowtype/shantell-sans)), licensed under the [SIL Open Font License 1.1](./OFL.txt). `fonts/Inter.ttf` is [Inter](https://fonts.google.com/specimen/Inter) by Rasmus Andersson, also OFL 1.1 ([`Inter-OFL.txt`](./Inter-OFL.txt)). Bundling each font with its license file satisfies the license terms. The committed assets contain outlined paths only.
