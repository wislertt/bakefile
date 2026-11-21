# CODING_STANDARDS.md

**Coding standards for bakefile, enforced in review**

Mechanical rules live in `ruff` and `ty` (`bake lint`). This file holds the judgement calls.

## Naming

- Name the variable `bakebook` (never `bakebook_app`, `bakebook_cli`), in user `bakefile.py` files, internal code, tests and docs.

## Types

- Put `Field()` inside `Annotated` (`Name = Annotated[str, Field(min_length=1)]`), not on the assignment.

## Docstrings

- Multi-line docstrings use NumPy format.

## Testing

- With the `mock_ctx` fixture, assert on captured stderr (`capsys`) instead of patching. Dry-run prints every command, so output shows what would run and in what order. Patch only for error paths that would end the test, external services, or complex dependencies.

```python
# Bad: patching run to capture commands
with mock_ctx, patch.object(mock_ctx, "run", side_effect=capture_run):
    utils.setup_tools()

# Good: read the dry-run output
with mock_ctx:
    utils.setup_tools()
err = strip_ansi(capsys.readouterr().err)
assert "git submodule update --init --recursive" in err
```

## Reference

Read the matching file when working in that area:

- Bakebook class, commands, env vars, context: `src/bake/bakebook/README.md`
- `console` output helpers and colors: `src/bake/ui/README.md`
- Verbosity and logging config (user-facing: `docs/site/usage/logging.mdx`): `src/bake/ui/logger/README.md`
- GitHub Actions caching: `CONTRIBUTING.md`
