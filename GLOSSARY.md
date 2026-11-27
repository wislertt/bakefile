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

## Managed content

**Managed content**:
Content in a project's files that a Space owns, so every project using that Space carries the same version. It takes one form: the managed file.
_Avoid_: generated file, snippet

**Managed file**:
A file a Space renders from a template, where the project edits only the editable blocks.
_Avoid_: generated file, template file, managed block

**Template**:
The source of a managed file: the text of the Space that declares it plus what child Spaces add, shipped at its latest version only in those Spaces' packages.
_Avoid_: blueprint, skeleton

**Template hook**:
A named spot in a template where child Spaces add text, which then belongs to the template like any other part, editable blocks included.
_Avoid_: hook (bare, which also names a method child Spaces extend with `super()`), insertion point, slot, fragment

**Editable block**:
A marked part of a template whose content the project owns and keeps across template upgrades.
_Avoid_: hole, editable (as a noun), region, managed block

**Bakefile value**:
A spot in a template that bake fills with text the Space gives in one mapping that child Spaces extend, rewritten on every write.
_Avoid_: slot, placeholder, variable (bare)

**`bake.lock`**:
The file at a project's root that records which managed files bake wrote and the editable blocks the project changed.
_Avoid_: lock (bare), lockfile, manifest, state file

**Adoption**:
Taking over an existing file that has no managed header, either because it already equals what bake would write apart from the header, or by moving its content into the one editable block its template marks for it.
_Avoid_: import, migration

**Detached file**:
A managed file a project has taken over by hand: its Spaces still declare it, but bake neither writes, checks nor deletes it.
_Avoid_: unmanaged file, ejected file

**Drift**:
A difference between the managed content on disk and what its Spaces would write now.
_Avoid_: out of sync, stale

## Migrations

**Migration**:
A one-off step a Space ships to move projects off something it no longer wants (a retired tool, a leftover file), applied only while the project still needs it and removed from the Space after its expiry date.
_Avoid_: upgrade step, codemod, adoption (that is taking over a headerless managed file)

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
