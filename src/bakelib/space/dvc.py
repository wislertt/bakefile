"""DvcSpace — bake mixin exposing direction-aware DVC verbs as ``bake dvc …``.

Blobs live in a content-addressed dvc cache pushed to a remote; ``.dvc``
metas travel via git; creds only as env vars, never on disk. Bare ``add``
walks ``dvc_track_globs`` — workspace is truth: an emptied dir records an
empty meta (a deletion); an absent dir is un-materialized (a pull state),
never a deletion signal.

    bake dvc add [path]    record workspace into meta (local, no creds)
    bake dvc push          upload new cache objects to the remote
    bake dvc pull [path]   fetch + materialize (never uploads)
    bake dvc gc            drop cache outside the keep-set (--cloud: remote too)
    bake dvc check         state report incl. forgot-to-push
    bake dvc ping          hard remote reachability probe (real creds)
"""

import configparser
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, ClassVar

import typer
from rich.text import Text

from bake import GroupKwargs, command, console, style
from bake._params import fast_option
from bakelib.space.base import BaseSpace
from bakelib.utils.secret import SecretUtils

DVC_GROUP = "dvc"


def _extras_for_url(url: str) -> tuple[str, ...]:
    """Mise extras for the dvc driver a remote url's scheme needs.

    Local paths and http(s) remotes need no extra; unknown schemes yield
    ``()`` too — the url is rejected at init before mise installs.
    """
    scheme = url.partition("://")[0]
    extras = {"hdfs": "hadoop", "webdavs": "webdav"}.get(scheme, scheme)
    if scheme in {
        "s3",
        "gs",
        "azure",
        "oss",
        "ssh",
        "webdav",
        "webdavs",
        "webhdfs",
        "hdfs",
    }:
        return (extras,)
    return ()


def _styled_path(path: str) -> Text:
    """Path as rich Text, final component colored — Text skips rich's
    markup and number highlighter, which would mangle paths."""
    parent, _, name = path.rpartition("/")
    text = Text(parent + "/") if parent else Text()
    text.append(name, style=style.BOLD_BLUE)
    return text


def _gc_args(days: int, depth: int, today: date, *, cloud: bool, dry: bool) -> list[str]:
    """dvc gc argv for the keep window; nets only widen the kept set."""
    args = ["gc", "--force", "--workspace", "--all-branches"]
    if days > 0:
        args += ["--date", (today - timedelta(days=days)).isoformat()]
    if depth > 1:
        args += ["--num", str(depth)]
    if dry:
        args.append("--dry")
    if cloud:
        args.append("--cloud")
    return args


class DvcSpace(SecretUtils[str | None], BaseSpace):
    """Space adding the ``bake dvc`` command group over a DVC remote.

    setup-dev converges `.dvc/config` to the remote attrs, probes the
    remote (fail-fast on bad url/creds) and installs both git hook
    stages. The consuming repo still provides:

    - ``.pre-commit-config.yaml``: a ``dvc push`` local hook at the
      pre-push stage (the install is done here, the hook entry is not)
    - a scheduled ``bake dvc gc --cloud`` run in CI (checkout with full
      history; the ``dvc_secret_keys`` as repo secrets exposed as env)

      Weekly is plenty and any frequency is safe: gc is idempotent, each
      pass re-derives the keep-set from origin and only deletes what no
      kept ref pins — and the pre-push ``dvc push`` hook keeps committed
      metas' objects on the remote, so unpinned objects are only WIP a
      machine still holds locally. Extra runs cost workflow minutes,
      nothing else.
    """

    def _get_mise_tools(self) -> set[str]:
        extras = ",".join(_extras_for_url(self.dvc_remote_url))
        spec = f"pipx:dvc[extras={extras}]" if extras else "pipx:dvc"
        return {*super()._get_mise_tools(), spec}

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["dvc"] = None
        return tools

    #: Secret keys injected into every remote verb; names double as env
    #: var names — what the dvc child process reads.
    dvc_secret_keys: ClassVar[tuple[str, ...]] = ()

    #: Globs bare `add` walks; default = every ``data`` dir at any depth.
    dvc_track_globs: ClassVar[tuple[str, ...]] = ("**/data",)

    #: Remote name in `.dvc/config`. No default guessed — a wrong guess
    #: silently spawns a second remote next to the committed one.
    dvc_remote_name: ClassVar[str] = ""

    #: Remote url — required; empty = misconfigured, caught at init and
    #: reported by check.
    dvc_remote_url: ClassVar[str] = ""

    #: Keep net 1: every commit newer than this many days survives gc
    #: (dvc ``--date``).
    dvc_keep_days: ClassVar[int] = 90

    #: Keep net 2: depth back from each branch tip (dvc ``--num``); tips
    #: are always kept, depth only widens.
    dvc_keep_commits: ClassVar[int] = 1

    def _get_default_exclude_patterns(self) -> set[str]:
        # dvc-tracked paths are gitignored, so `git clean -fdX` would
        # delete the binaries and the cache; the / prefix converts the
        # python globs to gitignore's root-anchored form.
        tracked = (f"/{pattern}" for pattern in self.dvc_track_globs)
        return {*super()._get_default_exclude_patterns(), ".dvc", *tracked}

    def _setup_project(self) -> None:
        super()._setup_project()
        self._ensure_dvc_remote()
        self._assert_dvc_remote()
        # bakelib installs only the pre-commit stage
        self.ctx.run("pre-commit install --hook-type pre-push")

    def lint(self) -> None:
        super().lint()
        self.dvc_check()  # exit 1 only for un-backed dirs — safe to block on

    @command(
        name="assert-setup-dev",
        help="Assert development environment setup (incl. dvc remote probe)",
    )
    def assert_setup_dev(
        self,
        fast: Annotated[
            int,
            fast_option(help="Skip steps: -f skips tests, -ff skips tests and lint"),
        ] = 0,
    ) -> None:
        super().assert_setup_dev(fast)
        # hard remote touch — lint's dvc_check only ever soft-skips it
        if fast < 2:
            self._assert_dvc_remote()

    def model_post_init(self, __context: Any, /) -> None:
        # presets never instantiate, so this fires once per subclass —
        # missing remote attrs die at import, not at the first dvc verb
        super().model_post_init(__context)
        missing = [
            f"dvc_remote_{kind}"
            for kind, value in (
                ("name", self.dvc_remote_name),
                ("url", self.dvc_remote_url),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"{type(self).__name__}: {' and '.join(missing)} empty — set "
                "them on the bakebook. Nothing is guessed."
            )

    # ── Typer wiring ──

    def get_group_kwargs(self) -> dict[str, GroupKwargs]:
        group_kwargs = super().get_group_kwargs()
        group_kwargs[DVC_GROUP] = GroupKwargs(help="Data storage via DVC")
        return group_kwargs

    # ── Plumbing ──

    def _dvc_env(self) -> dict[str, str]:
        """Full child env plus remote creds (never written to disk)."""
        env = dict(os.environ)
        missing: list[str] = []
        for key in self.dvc_secret_keys:
            value = self.get_secret(key)
            if value:
                env[key] = value
            else:
                missing.append(key)
        if missing:
            console.error(
                "Missing DVC remote credentials. Set them with:\n"
                + "\n".join(f"  bake secret set {key} <value>" for key in missing)
            )
            raise typer.Exit(1)
        return env

    def _remote_env(self) -> dict[str, str] | None:
        """Like ``_dvc_env`` but soft: None instead of exiting when creds
        are missing — check degrades to local-only with a note."""
        env = dict(os.environ)
        for key in self.dvc_secret_keys:
            value = self.get_secret(key)
            if not value:
                return None
            env[key] = value
        return env

    def _dvc_run(self, *args: str, env: dict[str, str] | None = None) -> None:
        self.ctx.run(["dvc", *args], env=env)

    def _data_status(self) -> dict[str, Any]:
        """``dvc data status --json`` payload; empty dict = clean."""
        result = self.ctx.run(
            ["dvc", "data", "status", "--json"],
            capture_output=True,
            check=False,
            stream=False,  # streamed capture arrives ANSI-wrapped, unparsable
        )
        return json.loads(result.stdout or "{}")

    def _glob_targets(self) -> list[str]:
        """Existing dirs matched by dvc_track_globs, sorted.

        Skips anything under a dot-dir — recursive globs would otherwise
        pick up site-packages dirs named ``data``.
        """
        return [
            p.as_posix()
            for pattern in self.dvc_track_globs
            for p in sorted(Path().glob(pattern))
            if p.is_dir() and not any(part.startswith(".") for part in p.parts)
        ]

    # ── Remote ensure (setup-dev) ──

    def _config_get(self, section: str, option: str) -> str | None:
        """Value from `.dvc/config`; dvc rewrites ``[remote "r2"]`` as
        ``['remote "r2"']`` — match on the stripped name."""
        config = configparser.ConfigParser()
        config.read(".dvc/config")
        for name in config.sections():
            if name.strip("'") == section:
                return config.get(name, option, fallback=None)
        return None

    def _ensure_dvc_remote(self) -> None:
        """Converge `.dvc/config` to the attrs — idempotent, no creds."""
        if not self.dvc_remote_url:
            console.error(
                "dvc_remote_url is empty — set it on the bakebook. No remote location is guessed."
            )
            raise typer.Exit(1)
        if not Path(".dvc").is_dir():
            self._dvc_run("init")
        name, url = self.dvc_remote_name, self.dvc_remote_url
        current_url = self._config_get(f'remote "{name}"', "url")
        if current_url is None:
            console.start(f"Adding dvc remote '{name}'")
            self._dvc_run("remote", "add", name, url)
        elif current_url != url:
            console.start(f"Updating dvc remote '{name}'")
            self._dvc_run("remote", "modify", name, "url", url)
        if self._config_get("core", "remote") != name:
            # `dvc remote add` does not set the default remote
            self._dvc_run("config", "core.remote", name)
        console.success(f"dvc remote '{name}' -> {url}")

    def _assert_dvc_remote(self) -> None:
        """Round-trip the remote — setup fails fast on bad url or creds.

        ``dvc ls-url`` is the cheapest guaranteed network touch — it
        lists the storage url directly (``dvc ls`` targets a git repo,
        not a remote); an empty remote lists empty and exits 0. Under a
        bake dry run ``ctx.run`` echoes the probe and fakes rc 0."""
        console.start(f"Probing dvc remote '{self.dvc_remote_name}'")
        result = self.ctx.run(
            ["dvc", "ls-url", self.dvc_remote_url],
            env=self._dvc_env(),
            check=False,
        )
        if result.returncode != 0:
            console.error(
                f"dvc remote '{self.dvc_remote_name}' unreachable "
                f"({self.dvc_remote_url}) — check the url and creds "
                "(bake secret set …)"
            )
            raise typer.Exit(1)
        console.success(f"remote '{self.dvc_remote_name}' reachable")

    # ── Verbs ──

    @command(
        name="ping",
        group_name=DVC_GROUP,
        help="Probe remote reachability with real creds (hard-fails)",
    )
    def dvc_ping(self) -> None:
        """Connectivity/creds debug verb — the hard check that ``check``
        and ``lint`` deliberately never are (both stay offline-tolerant).
        Same probe ``setup-dev`` and ``assert-setup-dev`` run."""
        self._assert_dvc_remote()

    @command(
        name="add",
        group_name=DVC_GROUP,
        help="Record workspace data into .dvc metas (local only, no creds)",
    )
    def dvc_add(
        self,
        path: Annotated[
            str | None,
            typer.Argument(help="Data dir or .dvc file; bare = walk dvc_track_globs"),
        ] = None,
    ) -> None:
        targets = [path] if path else self._glob_targets()
        if not targets:
            console.echo("Nothing to add: no data dirs match dvc_track_globs.")
            return
        for target in targets:
            self._dvc_run("add", target)

    @command(
        name="push",
        group_name=DVC_GROUP,
        help="Upload new cache objects to the remote",
    )
    def dvc_push(self) -> None:
        console.start("Pushing cache objects to the remote")
        self._dvc_run("push", env=self._dvc_env())
        console.success("remote now has every object the local cache references")

    @command(
        name="pull",
        group_name=DVC_GROUP,
        help="Fetch + materialize data from the remote (never uploads or deletes)",
    )
    def dvc_pull(
        self,
        path: Annotated[
            str | None,
            typer.Argument(help="Data dir or .dvc file; bare = everything"),
        ] = None,
    ) -> None:
        console.start("Pulling data from the remote")
        if path:
            self._dvc_run("pull", path, env=self._dvc_env())
        else:
            self._dvc_run("pull", env=self._dvc_env())
        console.success("workspace matches the committed metas")

    def _fetch(self, cloud: bool) -> None:
        """``git fetch --prune``; best-effort locally, hard-fail when
        ``cloud`` — a partial origin view would sweep sibling machines'
        objects."""
        result = self.ctx.run(["git", "fetch", "--prune"], check=False)
        if result.returncode != 0:
            if cloud:
                console.error("git fetch failed — gc --cloud needs every origin branch")
                raise typer.Exit(1)
            console.warning("git fetch failed — keeping local branches only")

    def _mirror_origin_branches(self) -> None:
        """Local branch per origin branch that has none — dvc
        ``--all-branches`` reads refs/heads only, and existing locals are
        never touched."""
        locals_ = set(
            self.ctx.run(
                ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"],
                capture_output=True,
            ).stdout.splitlines()
        )
        remotes = self.ctx.run(
            ["git", "for-each-ref", "--format=%(refname)", "refs/remotes/origin"],
            capture_output=True,
        ).stdout.splitlines()
        for ref in remotes:
            if ref.endswith("/HEAD"):
                continue
            branch = ref.removeprefix("refs/remotes/origin/")
            if branch not in locals_:
                self.ctx.run(["git", "branch", branch, ref])

    @command(
        name="gc",
        group_name=DVC_GROUP,
        help="Drop cache objects outside the keep-set (--cloud: the remote too)",
    )
    def dvc_gc(
        self,
        cloud: Annotated[
            bool,
            typer.Option("--cloud", help="Also sweep the remote, not just the local cache"),
        ] = False,
    ) -> None:
        """Keep-set, one pass, dvc keeps the union:

        - workspace
        - every branch tip, plus ``dvc_keep_commits`` commits back from
          it (default 1 = tip only; sent as ``--all-branches``/``--num``)
        - every commit newer than ``dvc_keep_days`` days

        The window comes from the attrs, not flags.

        dvc's ``--rev`` is single-value (repeating the flag is
        last-wins), so ``--all-branches`` is the only multi-tip form.

        A ``--cloud`` sweep is preceded by a hard-failing fetch-prune
        plus origin-branch mirroring, so sibling machines' objects
        survive wherever it runs."""
        days = self.dvc_keep_days
        depth = self.dvc_keep_commits
        dry = self.ctx.dry_run
        # gc is the one verb with native safe-dry semantics (--dry deletes
        # nothing), so a bake-level dry run executes the whole pipeline for
        # real — a rehearsal that skipped its commands would rehearse
        # nothing. Every other verb keeps the show-skip behavior.
        with self.ctx.override_dry_run(False):
            self._fetch(cloud)
            if cloud:
                self._mirror_origin_branches()
            args = _gc_args(days, depth, datetime.now(tz=timezone.utc).date(), cloud=cloud, dry=dry)
            env = self._dvc_env() if cloud else None
            scope = "remote" if cloud else "local cache"
            console.start(
                f"Running dvc gc ({scope}; keep {days}d"
                + (f", depth {depth}" if depth > 1 else "")
                + ")"
            )
            self._dvc_run(*args, env=env)
        if dry:
            console.success("dry run — nothing removed")
        else:
            console.success("cache now holds only keep-set objects")

    @command(
        name="check",
        group_name=DVC_GROUP,
        help="Report drift, un-materialized dirs, uncommitted metas, un-pushed objects",
    )
    def dvc_check(self) -> None:
        """State report. Problems (exit 1) are git↔dvc consistency breaks:
        un-backed dirs (data with no pointer at all), drift, untracked
        data, untracked or unstaged metas, an empty ``dvc_remote_url``.
        Warnings (exit 0) are transfer gaps only: un-materialized dirs
        (bytes on remote, missing locally) and un-pushed objects. The
        remote pass (``data status --not-in-remote``) soft-skips without
        creds; the local report still runs."""
        if not Path(".dvc").is_dir():
            console.echo("No dvc repo — nothing to check.")
            return
        problems: list[tuple[str, str]] = []
        warnings: list[tuple[str, str]] = []
        needs_add = False
        has_metas = False
        unstaged = False
        needs_pull = False
        needs_push = False

        status = self._data_status()
        not_in_cache = set(status.get("not_in_cache", []))
        uncommitted = status.get("uncommitted", {})
        for target in sorted(not_in_cache | set(uncommitted.get("deleted", []))):
            # meta + remote intact, bytes just missing locally — pull restores,
            # git tree stays consistent: transfer gap, not a break
            warnings.append(("un-materialized", target))
            needs_pull = True
        for kind, targets in uncommitted.items():
            if kind == "deleted":
                continue  # already reported as un-materialized above
            for target in targets:
                if target in not_in_cache:
                    continue
                problems.append(("drift", target))
                needs_add = True
        if not self.dvc_remote_url:
            problems.append(("no remote url", "dvc_remote_url"))
        elif (env := self._remote_env()) is None:
            console.echo(style.dim("(remote check skipped: missing creds — bake secret set …)"))
        else:
            result = self.ctx.run(
                ["dvc", "data", "status", "--json", "--not-in-remote"],
                capture_output=True,
                check=False,
                stream=False,
                env=env,
            )
            if result.returncode != 0:
                console.warning("remote check failed — un-pushed state unknown")
            else:
                not_in_remote = set(json.loads(result.stdout or "{}").get("not_in_remote", []))
                for target in sorted(not_in_remote):
                    warnings.append(("un-pushed", target))
                    needs_push = True
        metas = self.ctx.run(["git", "status", "--porcelain", "--", "*.dvc"], capture_output=True)
        for line in metas.stdout.splitlines():
            xy, path = line[:2], line[3:]
            if xy == "??":
                problems.append(("untracked meta", path))
                has_metas = True
            elif xy[1] != " ":
                problems.append(("unstaged meta", path))
                has_metas = True
                unstaged = True
        for target in self._glob_targets():
            if not Path(f"{target}.dvc").is_file():
                problems.append(("untracked data", target))
                needs_add = True

        if not problems and not warnings:
            console.success("dvc state clean: workspace matches metas, all metas staged")
            return

        def emit(items: list[tuple[str, str]]) -> None:
            width = max(len(label) for label, _ in items)
            for label, path in items:
                console.echo(Text(f"  {label.ljust(width)}  ") + _styled_path(path))

        if problems:
            console.error(f"{len(problems)} problem(s):")
            emit(problems)
        if warnings:
            if problems:
                console.echo("")
            console.warning(f"{len(warnings)} warning(s):")
            emit(warnings)
        # required = fix a consistency break (the problems above);
        # optional = transfer gaps only — skip freely if bytes not needed.
        required: list[tuple[str, str]] = []
        if needs_add:
            required.append(("fix", "bake dvc add"))
        if has_metas:
            # glob, not paths: stages exactly what this report flagged
            required.append(("stage", "git add '*.dvc'"))
        optional: list[tuple[str, str]] = []
        if needs_pull:
            optional.append(("pull", "bake dvc pull"))
        if needs_push:
            optional.append(("push", "bake dvc push"))
        if required or optional:
            console.echo("")
            console.echo(style.dim("remedies:"))

            def emit_remedies(items: list[tuple[str, str]], indent: str) -> None:
                width = max(len(label) for label, _ in items)
                for label, remedy in items:
                    console.echo(f"{indent}{label.ljust(width + 1)} {style.code(remedy)}")

            if required:
                console.echo(style.dim("  required:"))
                emit_remedies(required, "    ")
            if optional:
                console.echo(style.dim("  optional:"))
                emit_remedies(optional, "    ")
        if unstaged:
            console.echo(
                style.dim(
                    "(unstaged meta = pushed-but-uncommitted gap: "
                    "other machines can't see the bytes)"
                )
            )
        if problems:
            raise typer.Exit(1)


class MediaDvcSpace(DvcSpace):
    """DvcSpace for repos whose blob dirs are called ``media/``."""

    dvc_track_globs: ClassVar[tuple[str, ...]] = ("**/media",)
