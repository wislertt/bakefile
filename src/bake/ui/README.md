# Console output

Coding rules live in `CODING_STANDARDS.md`.

## Color Output

### Console Output Pattern

**Use the `console` module from `bakefile.ui` for all user-facing output:**

```python
from bake.ui import console

# Success messages (green, stderr)
console.success("Operation completed")

# Echo messages (plain, stdout, accepts any type)
console.echo("Processing data")
console.echo({"key": "value"})  # prints dict
console.echo(42)  # prints number

# Warning messages (yellow, stderr)
console.warning("File not found")

# Error messages (red, stderr)
console.error("Failed to connect")

# Custom labeled line (when built-in labels don't fit)
# label is required — use info() for the default INFO label
console.prefix("Deployed", label="DEPLOY", label_style="bold magenta")

# Command echo (arrow is chrome, command text always plain)
console.cmd("bake build")
console.cmd(cmd_str, arrow_style="bold red")  # e.g. echo a failed command
```

**Rich Markup in Messages:**

You can use Rich's `[tag]text[/tag]` markup syntax for emphasis:

```python
# Highlight paths or commands
console.error(f"File [bold]{path}[/bold] already exists")
console.info(f"Run [code]bakefile init --inline[/code] to create one")

# Common markup tags
# [bold], [italic], [underline]
# [red], [green], [yellow], [blue], [cyan], [magenta]
# [code] or backticks for monospace
```

**Markup kwarg scope (labeled helpers):**

- Rich print kwargs (`style`, `emoji`, `markup`, `highlight`, ...) apply to the **message only** — the label chrome is a `Text` object and never affected. Chrome styling uses its own params (`label_style` on `prefix`, `arrow_style` on `cmd`) so rich kwargs are never shadowed
- `console.success("tests[unit] passed", markup=False)` keeps the green label, prints message literally
- With markup on (default), rich parses the message: `[unit]`-style tags are consumed, stray `[/tag]` raises `MarkupError`
- For message text that may contain brackets (paths, globs, subprocess output), pass `markup=False`

**Stream separation:**

- `echo()` → stdout: machine-readable data (values meant for piping/capture)
- Everything else (`info`, `success`, `start`, `end`, `warning`, `error`, `cmd`, `block`) → stderr: human progress output

This keeps `bake my-task | grep value` clean: data on stdout, progress noise on stderr.

**Delimiting output sections:**

- Prefer `block()` context manager — exception-safe (closing line printed in `finally`)
- Avoid `start()`/`end()` pairs — easy to forget the matching `end()`, no guard
- `line()`/`thin_line()` for manual separators

```python
with console.block("Running tests"):
    bakebook.ctx.run("pytest")
```

**Plain (no-color) output:**

- Any console function accepts `no_color=True` to emit zero ANSI codes (labels get `[INFO]`-style brackets)
- Use for machine-parseable output: `console.echo(value, no_color=True)`
- Emoji glyphs (✅ ⚠️ ❌) still render — they are unicode, not ANSI

**Type hints:**

- `success(message: str)`, `warning(message: str)`, `error(message: str)` - strings only
- `info(message: Any)` - accepts any object type

### Respect NO_COLOR Environment Variable

Single gate: `bake_settings.colors_enabled()` in `bake/utils/settings.py`.
False is absolute (no color anywhere); True only permits — per-call knobs
(console `no_color=`, `run(color=False)`) can still opt out. Field
`bake_settings.no_color` is a sticky off-switch (env/.env at startup);
the live env read keeps runtime changes working.

The console module applies the gate at console construction:

- Colors enabled: Labels show as "SUCCESS", "WARNING", "ERROR"
- NO_COLOR set (non-empty, per no-color.org): Labels show as "[SUCCESS]", "[WARNING]", "[ERROR]"
- Empty string counts as unset

Child processes: `run()` forwards the decision via `FORCE_COLOR` /
`CLICOLOR_FORCE` injection (or `NO_COLOR=1` with `color=False`). See
`_apply_color_env` in `bake/ui/run/main.py`.

---
