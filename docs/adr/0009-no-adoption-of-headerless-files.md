---
status: accepted, supersedes the "Header and adoption" section of ADR-0006
---

# No adoption of headerless managed files

ADR 0006 let a template mark one editable block as the adopt block (`{% editable <name> adopt %}`), and a file at the managed path without the header was moved into that block verbatim. That only worked for ignore files and markdown, so a headerless file meant two different flows depending on its type. In practice the kept content often repeated the managed section it now sat beside, and in `.gitignore` it came last, so its rules overrode the managed ones. Each adopted file then needed cleanup by hand anyway.

Adoption is removed. A headerless file at a managed path is handled the same way for every file type: `bake mc sync` exits 2 with nothing written and the project chooses between `bake mc sync --force`, which writes the template with default editable blocks (the old content stays in git history), and `.detach()` on the file's entry in `_get_managed_files()`, which keeps it as is. Taking over a headerless file that already equals what bake would write apart from the header stays, since nothing is lost there.

An `adopt` option on an editable block tag is now a malformed tag, so a template still written for adoption fails at load instead of silently becoming a plain editable block.
