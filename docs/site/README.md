# Docs

This directory is the [Mintlify](https://mintlify.com) site published at [bakefile.wisl.dev](https://bakefile.wisl.dev). Check broken links with `bake docs-check`.

## Agent surfaces

Mintlify serves machine-readable endpoints for AI agents automatically:

- `llms.txt` and `llms-full.txt` are auto-generated from the navigation in `docs.json`. Zero maintenance.
- `/mcp` is a search MCP server over the docs. Zero maintenance.
- `skill.md` is hand-written and served at `/skill.md`; it overrides the low-quality file Mintlify auto-generates. Do not delete it. It is served raw, so it cannot carry MDX-only components — every code example in it must be a verbatim copy of a tested source (`examples/*/bakefile.py` or an example in a `.mdx` page).
- `markdown.instructions` in `docs.json` is injected as an `Agent Instructions` block into `llms.txt`, `llms-full.txt`, and every Markdown page export.

The `bake` and `bakefile` CLI help epilogs advertise these endpoints (`AGENT_DOCS_EPILOG` in `src/bake/cli/common/app.py`), and unit tests in `tests/unit/bake/cli/` assert they stay there.
