import logging
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import typer

from bake.ui import console
from bake.ui.run import run
from bakelib.refreshable_cache.cache import CachedT, CacheEntry, RefreshableCache
from bakelib.refreshable_cache.utils import FetchFn

logger = logging.getLogger(__name__)

#: SSOT for the age identity path; lives in this leaf module because both
#: the space and cache layers need it and the cache layer must not import spaces.
DEFAULT_AGE_KEY_FILE = Path.home() / ".config" / "fnox" / "age.txt"
#: Per-project cache file: lives next to ``fnox.toml``, gitignored — committed
#: config holds references only.
FNOX_LOCAL_FILE = "fnox.local.toml"
#: Gitignore pattern; bootstrap treats any existing ``*.local.toml`` line as
#: already covering the cache file.
FNOX_GITIGNORE_LINE = "*.local.toml"
#: Provider name inside the cache file. MUST differ from any committed project
#: provider: fnox replaces same-named providers as a unit (no deep-merge), so
#: ``[providers.age]`` here would clobber the project's for every fnox read.
FNOX_CACHE_PROVIDER = "bake-cache-age"
#: Env override for the cache store; read at call time, not import.
FNOX_CACHE_FILE_ENV = "BAKE_FNOX_CACHE_FILE"


def run_fnox(cmd: list[str] | tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Spawn ``fnox`` through the universal runner, secret-safe and colorless.

    Values are secrets: argv (``set``) and stdout (``get``) must never be
    echoed, streamed, or logged — ``redact=True`` keeps them out of bake's
    DEBUG entries and failure dumps, ``echo=False`` off the console.

    ``color=False`` keeps the chain colorless: bake's runner force-sets
    ``FORCE_COLOR``/``CLICOLOR_FORCE`` for captured children, and CLIs in
    fnox's own child chain like ``bws`` then emit ANSI-colored JSON that
    fnox's parser rejects. (For anything ``color=False`` can't tame, the
    ``env`` override — ``None`` = remove a var entirely — is the escape
    hatch.)
    """
    try:
        return run(
            ["fnox", *cmd],
            stream=False,
            capture_output=True,
            check=False,
            echo=False,
            redact=True,
            color=False,
        )
    except FileNotFoundError as e:
        msg = _fnox_missing_error()
        raise RuntimeError(msg) from e


@dataclass(frozen=True)
class BootstrapFetchFn(FetchFn[str]):
    """Chicken-and-egg provider credential: the local age-encrypted store is
    the ONLY source (the provider needs this very credential), so a miss is
    an actionable error, not a silent None."""

    label: str = "bootstrap secret"

    def __call__(self) -> str:
        console.error(f"{self.key} is not stored — run `bake setup-fnox` to store {self.label}")
        raise typer.Exit(1)


def _auth_failed_hint(stderr: str) -> str | None:
    if "auth_failed" not in stderr:
        return None
    return (
        "Provider auth failed — its bootstrap credential is missing or rejected. "
        "Rerun setup-dev's fnox step (`bake setup-fnox`) to re-store it; if the "
        "provider's env var (e.g. BWS_ACCESS_TOKEN / FNOX_BWS_ACCESS_TOKEN) is "
        "exported in your shell, it may be stale — env wins over the store."
    )


@dataclass(frozen=True)
class FnoxFetchFn(FetchFn[str]):
    """FetchFn that shells out to ``fnox get`` (see ``run_fnox`` for the
    leak-safety constraints)."""

    profile: str | None = None

    def __call__(self) -> str:
        cmd = ["--no-daemon"]
        if self.profile is not None:
            cmd += ["--profile", self.profile]
        cmd += ["get", self.key]
        result = run_fnox(cmd)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            # first stderr line only: fnox's own summary, not a stack dump
            summary = stderr.splitlines()[0] if stderr else "unknown error"
            console.error(f"fnox get {self.key} failed: {summary}")
            if hint := _auth_failed_hint(stderr):
                console.error(hint)
            raise typer.Exit(1)
        return (result.stdout or "").strip()


class FnoxCache(RefreshableCache[CachedT]):
    """Cache backend storing values age-encrypted in a local fnox-managed file.

    Spawns via ``run_fnox`` (see its docstring for the leak-safety
    constraints; ``set`` adds ``check=True``-style handling manually).
    """

    age_key_file: ClassVar[Path | None] = None
    cache_file: ClassVar[Path | None] = None

    def _cache_file(self) -> Path:
        if self.cache_file is not None:
            return self.cache_file
        if env := os.environ.get(FNOX_CACHE_FILE_ENV):
            return Path(env)
        return _project_root() / FNOX_LOCAL_FILE

    def _age_key_file(self) -> Path:
        return self.age_key_file or DEFAULT_AGE_KEY_FILE

    def _get_full_key(self) -> str:
        # fnox secret names must be valid env-var names (letters/digits/
        # underscores) — "namespace:key" from the base class is rejected.
        # re.ASCII keeps \W identical to the spelled-out [^A-Za-z0-9_]
        # (without it \W would spare non-ascii word chars like é)
        return re.sub(r"\W", "_", f"{self._namespace}__{self._key}", flags=re.ASCII)

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        logger.debug(
            f"FnoxCache: getting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        result = self._fnox(["get", self._get_full_key()])
        if result.returncode != 0:
            logger.debug(
                f"FnoxCache: cache miss for namespace='{self._namespace}', key='{self._key}'"
            )
            return None
        logger.debug(f"FnoxCache: cache hit for namespace='{self._namespace}', key='{self._key}'")
        return self._deserialize_entry((result.stdout or "").encode())

    def set(self, value: CachedT) -> None:
        logger.debug(
            f"FnoxCache: setting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        self._ensure_cache_file()
        data = self._serialize_entry(value).decode()
        self._fnox(
            ["set", self._get_full_key(), data, "--provider", FNOX_CACHE_PROVIDER], check=True
        )
        logger.debug(
            f"FnoxCache: successfully set entry for "
            f"namespace='{self._namespace}', key='{self._key}'"
        )

    def delete(self) -> None:
        logger.debug(
            f"FnoxCache: deleting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        result = self._fnox(["remove", self._get_full_key()])
        if result.returncode != 0:
            logger.debug(
                "FnoxCache: entry not found for deletion "
                f"(namespace='{self._namespace}', key='{self._key}')"
            )

    def _fnox(self, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
        cmd = ["--no-daemon", "-c", str(self._cache_file()), *args]
        result = run_fnox(cmd)
        if check and result.returncode != 0:
            # stderr only: argv/stdout may carry the secret value
            stderr = (result.stderr or "").strip()
            summary = stderr.splitlines()[0] if stderr else "unknown error"
            console.error(f"fnox {args[0]} failed: {summary}")
            if hint := _auth_failed_hint(stderr):
                console.error(hint)
            raise typer.Exit(1)
        return result

    def _ensure_cache_file(self) -> None:
        cache_file = self._cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        _ensure_gitignored(cache_file)
        if cache_file.exists() and cache_file.stat().st_size > 0:
            return
        key_file = self._age_key_file()
        if not key_file.exists():
            msg = f"age key not found: {key_file} — run `bake setup-fnox`"
            raise RuntimeError(msg)
        pubkey = _age_pubkey(key_file)
        logger.debug(f"FnoxCache: bootstrapping cache file '{cache_file}'")
        cache_file.write_text(
            f'[providers.{FNOX_CACHE_PROVIDER}]\ntype = "age"\n'
            # as_posix: backslashes would be invalid TOML basic-string escapes
            f'key_file = "{key_file.as_posix()}"\nrecipients = ["{pubkey}"]\n'
        )
        cache_file.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _project_root() -> Path:
    root_markers = (".git", "fnox.toml", "bakefile.py")
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if any((candidate / marker).exists() for marker in root_markers):
            return candidate
    return Path.cwd()


def _ensure_gitignored(cache_file: Path) -> Path:
    gitignore = cache_file.parent / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(f"{FNOX_GITIGNORE_LINE}\n")
        return gitignore
    lines = [line.strip() for line in gitignore.read_text().splitlines()]
    covered = {FNOX_GITIGNORE_LINE, "fnox.local.toml"}
    if covered & set(lines):
        return gitignore
    gitignore.write_text(gitignore.read_text() + f"{FNOX_GITIGNORE_LINE}\n")
    return gitignore


def _age_pubkey(key_file: Path) -> str:
    age_keygen = shutil.which("age-keygen")
    if age_keygen is None:
        msg = "age-keygen not found. Install it (`mise install age`) or run `bake setup-dev`."
        raise RuntimeError(msg)
    result = subprocess.run(
        [age_keygen, "-y", str(key_file)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        msg = f"age-keygen -y {key_file} failed: {(result.stderr or '').strip()}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _fnox_missing_error() -> str:
    found = shutil.which("fnox")
    if found is not None and "shims" in Path(found).parts:
        return (
            "fnox shim cannot resolve outside a mise-configured dir. "
            "Run from a project with fnox in .mise.toml, or `mise use -g fnox`."
        )
    return (
        "fnox not found. Install it (`mise install fnox`) or run `bake setup-dev` in your project."
    )
