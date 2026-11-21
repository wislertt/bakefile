# Loose floors for libraries, exact pins in a `locked` extra

`[project.dependencies]` holds true minimum floors so library consumers keep resolver freedom. `[project.optional-dependencies.locked]` holds exact `==` pins for using bakefile as a CLI, the way `uvx` or `uv tool install` runs it (`uv tool install "bakefile[locked]"`), giving them a reproducible tested set. The alternative, one exact-pinned list, would break library consumers; one loose list would make tool installs drift.

Pins change only through `bake update`: it relaxes non-held pins to their floors, runs `uv lock --upgrade`, then re-pins from `uv.lock`. The order matters, because exact pins cap their own upgrade if they are left in place. Renovate is disabled for these entries, and a `# hold` comment exempts a pin. The invariants are enforced by `scripts/locked_pins.py` inside `bake lint`.
