# bakefile

A Python task runner (Make/Justfile alternative) where tasks are methods on reusable, composable classes, so task logic can be inherited and shared across projects.

## Language

**bakefile**:
The product: the PyPI package and this repository. Names neither the file nor the management command.
_Avoid_: using "the bakefile" for the file, "bakefile project"

**`bakefile.py`**:
The user's task definition file, the Python equivalent of a Makefile. Always written with the extension.
_Avoid_: `bakefile` (bare), Makefile

**Global `bakefile.py`**:
The `bakefile.py` in the user's global bake directory, holding commands meant to be usable from any directory.
_Avoid_: global bake, global config, user bakefile

**Invocation directory**:
The directory the user ran `bake` or `bakefile` from, as opposed to the directory of the `bakefile.py` the commands run in.
_Avoid_: cwd, user working dir

**Bakebook**:
A class that holds commands and variables, so tasks can be composed, inherited and reused. A `bakefile.py` exposes one.
_Avoid_: recipe, task class, bake book

**Space**:
A reusable Bakebook mixin that gives a project a set of commands for one concern or project type (Python library, DVC, fnox).
_Avoid_: recipe, template, plugin

**`bake` CLI**:
The command that loads a `bakefile.py` and runs its Bakebook commands.

**`bakefile` CLI**:
The command that manages `bakefile.py` files and their environments (init, lint, add, lock, sync).
_Avoid_: `bakefile` (bare)

**bakelib**:
The optional library of prebuilt Spaces and utilities, installed with the `lib` extra. An extension built on `bake`; `bake` never imports it.

## Python environments

**Bakefile-level**:
A `bakefile.py` with its own PEP 723 inline metadata and an isolated environment.
_Avoid_: standalone (in prose), script mode

**Project-level**:
A `bakefile.py` with no inline metadata, which uses the surrounding project's environment.

## Dependency pins

**Locked extra**:
The `locked` optional-dependency group of exact pins, which gives tool installs a reproducible tested set. Library consumers use the loose floors instead.
_Avoid_: lockfile (that is `uv.lock`)

**Hold**:
A pin marked with a trailing `# hold` comment so `bake update` leaves it alone.
_Avoid_: freeze, pin-lock

## Secrets

**Fetch function**:
A callable that obtains one secret's value from its origin (for example a remote vault).
_Avoid_: provider, loader

**Refreshable cache**:
A disposable local layer over fetch functions that stores secret values with a TTL and refetches when stale.
_Avoid_: secret store, vault (the vault is the registry that wires caches to fetch functions)

**Bootstrap secret**:
A tracked secret that a provider needs before it can fetch any other secret (for example a vault access token).
_Avoid_: root secret, seed credential
