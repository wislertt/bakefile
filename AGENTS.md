# AGENTS.md

**bakefile** is a Python task runner (Make/Justfile alternative) that uses OOP for task reuse, and manages tasks for any project type. Two CLIs: `bake` runs tasks from `bakefile.py`; `bakefile` manages bakefile.py files and their environments.

## Read before working

- Before adding or editing code: `CODING_STANDARDS.md` (coding standards, including test conventions).
- Vocabulary: `GLOSSARY.md`. Why things are the way they are: `docs/adr/`.
- Architecture and load flow: `docs/reference/architecture.md`.
- Bakebook class, commands, env vars, context: `src/bake/bakebook/README.md`. Console output helpers: `src/bake/ui/README.md`. Logging config: `src/bake/ui/logger/README.md`.
- GitHub Actions caching: `CONTRIBUTING.md`.
- When something fails or behaves oddly: `docs/troubleshooting/`.
- Before writing tests: `tests/README.md`.
- Commands: `bake --help` (`bake lint`, `bake test`, `bake test-integration`).

## Working rules

- Run targeted tests (`uv run pytest <path>::<test> -v`) during development. The full suite takes about 80 seconds; the developer runs `bake test` before committing.
- Write no docstrings, not even placeholders; the developer adds them where needed.
- Do not commit automatically.
- When working from a task list, do exactly the task named (e.g. "1.1") and stop for review.

## Trying a Space for real (`bakebook2` pattern)

Unit tests mock commands; real UX needs a real `bake` run. Add a temporary second bakebook at the bottom of `bakefile.py`, a subclass of the Space under test that exposes its private steps:

```python
# TEMP: try <Space> for real (remove after evaluation)
class Trybook(SomeSpace[str | None]):
    @command(name="foo-setup", help="Run only the foo part of setup-dev")
    def foo_setup(self) -> None:
        self._ensure_foo()


bakebook2 = Trybook()
```

Run it with `bake -b bakebook2 foo-setup` (or any `bakebook2` command, e.g. `bake -b bakebook2 setup-dev -ff`). Remove the TEMP block after evaluation.

## Agent skills

### Issue tracker

Local markdown under `.tracker/` (committed), never `.scratch/`; GitHub Issues on `wislertt/bakefile` only when I ask for it. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.
