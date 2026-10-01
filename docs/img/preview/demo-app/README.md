# bakefile-preview.gif

Terminal preview GIF used in README and directory listings (Terminal Trove, etc).

## Dependencies

- [vhs](https://github.com/charmbracelet/vhs) >= 0.12.1 (0.12.0 has a bug where no output file is written: charmbracelet/vhs#787)
- bakefile (`uv tool install bakefile` or `pip install bakefile`)
- cargo
- bat
- ffmpeg + uv + project dev deps with Pillow (still PNG only)

## Theme

The tape uses a custom theme built from the site palette: background `#152A40`
(`--background-dark`), primary `#4F8CC8`, cream `#DDB283` (`--sd-cream`).

## Render

```bash
cargo build          # once, so `bake build` finishes fast
vhs bakefile.tape    # writes bakefile-preview.gif in this directory
```

## Still PNG

`bakefile-preview.png` is a two-column still rendered by separate tapes (not
part of `bakefile.tape`, so re-render it with the script, not `vhs bakefile.tape`):

- left: `bakefile.py` via `bat` (`bat-png.tape`)
- right: `bake --help`, usage header plus the Commands panel and docs footer;
  the Options panel is cropped out (`help-png.tape`, a 860x2200 terminal so
  nothing scrolls)

```bash
./render-png.sh      # renders both tapes and composes bakefile-preview.png
```

`compose-png.py` holds the crop offsets; they are tuned to the tapes' fixed
sizes, so if the help text changes, re-check them against the extracted frames.
