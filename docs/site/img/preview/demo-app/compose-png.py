"""Composite bakefile-preview.png from the two PNG tape renders.

Left column: bakefile.py via bat (bat-png.gif, full frame cropped to content).
Right column: bake --help (help-png.gif), usage header stacked above the
Commands panel + docs footer; the Options panel is left out.

Crop offsets are tuned to the tapes' fixed sizes (640x800 and 860x2200,
FontSize 18). If the command output text changes, re-check them.
"""

from PIL import Image

DIVIDER = (0x48, 0x67, 0x8A)

left = Image.open("bat-last.png").crop((0, 0, 640, 490))

help_img = Image.open("help-last.png")
right_top = help_img.crop((0, 42, 860, 168))  # prompt, usage, description
right_bottom = help_img.crop((0, 1375, 860, 1695))  # Commands, docs footer, prompt

height = max(left.height, right_top.height + 10 + right_bottom.height)
out = Image.new("RGB", (left.width + 3 + right_top.width, height), "#0E1C2C")
out.paste(left, (0, 0))
out.paste(Image.new("RGB", (3, height), DIVIDER), (left.width, 0))
out.paste(right_top, (left.width + 3, 0))
out.paste(right_bottom, (left.width + 3, right_top.height + 10))
out.save("bakefile-preview.png")
print(f"bakefile-preview.png {out.size[0]}x{out.size[1]}")
