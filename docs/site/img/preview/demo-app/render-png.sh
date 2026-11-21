#!/usr/bin/env bash
# Render bakefile-preview.png: bat view of bakefile.py (left) next to
# bake --help (right), cropped and composited. See README.md ("Still PNG").
set -euo pipefail
cd "$(dirname "$0")"

vhs bat-png.tape
vhs help-png.tape
ffmpeg -y -loglevel error -sseof -1 -i bat-png.gif -update 1 -frames:v 1 bat-last.png
ffmpeg -y -loglevel error -sseof -1 -i help-png.gif -update 1 -frames:v 1 help-last.png

uv run python compose-png.py

rm -f bat-png.gif help-png.gif bat-last.png help-last.png
