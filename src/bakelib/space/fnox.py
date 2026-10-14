import os
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, ClassVar, TypeVar, cast

import typer

from bake import command
from bake._params import fast_option
from bake.ui import console
from bakelib.refreshable_cache.fnox import DEFAULT_AGE_KEY_FILE, BootstrapFetchFn
from bakelib.refreshable_cache.registry import (
    RefreshableCacheRegistry,
    SecretUtilsFnoxCacheRegistry,
)
from bakelib.refreshable_cache.utils import FetchFn
from bakelib.space.base import BaseSpace
from bakelib.utils.secret import SecretUtils

T = TypeVar("T")


class FnoxSpace(SecretUtils[T], BaseSpace):
    fnox_age_key_file: Path | None = None

    #: Chicken-and-egg credentials fnox's own providers need before any remote
    #: fetch works — fnox resolves provider credentials from ENV ONLY, so these
    #: are stored in the local vault (paste via ``bake setup-fnox``) and exported
    #: to env when the vault is built (env wins). ``FNOX_<PROVIDER>_*`` names;
    #: base is empty (having fnox says nothing about which provider).
    fnox_bootstrap_secrets: ClassVar[Mapping[str, str]] = {}

    _cache_registry_cls: ClassVar[type[RefreshableCacheRegistry[Any]]] = (
        SecretUtilsFnoxCacheRegistry[T]
    )

    def _age_key_file(self) -> Path:
        return self.fnox_age_key_file or DEFAULT_AGE_KEY_FILE

    def get_secret_fetch_fns(self) -> tuple[FetchFn[T], ...]:
        return (
            *super().get_secret_fetch_fns(),
            *(
                cast("FetchFn[T]", BootstrapFetchFn(key=name, label=label))
                for name, label in self.fnox_bootstrap_secrets.items()
            ),
        )

    def _setup_vault(self, vault: RefreshableCacheRegistry[T]) -> None:
        # fnox reads provider credentials from env only; env (CI/user shell) wins
        for name in self.fnox_bootstrap_secrets:
            if not os.environ.get(name) and vault.has_value(name):
                os.environ[name] = cast("str", vault.get(name))

    def _get_mise_tools(self) -> set[str]:
        return {*super()._get_mise_tools(), "age", "fnox"}

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["age"] = None
        tools["fnox"] = None
        return tools

    def _setup_project(self) -> None:
        super()._setup_project()
        self._ensure_age_key()
        self._ensure_bootstrap_secrets()

    def assert_setup_dev(
        self,
        fast: Annotated[
            int,
            fast_option(help="Skip steps: -f skips tests, -ff skips tests and lint"),
        ] = 0,
    ) -> None:
        super().assert_setup_dev(fast)
        self._assert_age_key()
        self._assert_bootstrap_secrets()

    @command(help="Run only the fnox part of setup-dev")
    def setup_fnox(self) -> None:
        self._ensure_age_key()
        self._ensure_bootstrap_secrets()

    def _ensure_age_key(self) -> None:
        key_file = self._age_key_file()
        if key_file.exists():
            console.success(f"age key: {key_file}")
            return
        console.start("Generating age key")
        if not self.ctx.dry_run:
            key_file.parent.mkdir(parents=True, exist_ok=True)
        self.ctx.run(["age-keygen", "-o", str(key_file)])
        console.success(f"age key: {key_file}")

    def _assert_age_key(self) -> None:
        # read-only check, safe under dry-run
        key_file = self._age_key_file()
        console.cmd(f"test -f {key_file}")
        if key_file.exists():
            console.success(f"age key: {key_file}")
        else:
            console.error(f"age key not found: {key_file} — run `bake setup-fnox`")

    def _ensure_bootstrap_secrets(self) -> None:
        # callers run _ensure_age_key() first — the store's provider needs it
        if not self.fnox_bootstrap_secrets:
            return
        vault = self.vault()
        for name, label in self.fnox_bootstrap_secrets.items():
            if vault.has_value(name):
                console.success(f"{name}: cached")
                continue
            if self.ctx.dry_run:
                console.info(f"Would prompt for {name} (dry run)")
                continue
            if not typer.confirm(
                f"Set {label} now (stored age-encrypted as {name})?", default=False
            ):
                console.info(
                    f"Skipped {name} — provider-backed fetches will fail auth until it is set "
                    "(rerun `bake setup-fnox`)"
                )
                continue
            token = typer.prompt(f"Paste your {label}", hide_input=True)
            self.set_secret(name, token)
            console.success(f"{name}: cached")

    def _assert_bootstrap_secrets(self) -> None:
        # read-only check, safe under dry-run
        if not self.fnox_bootstrap_secrets:
            return
        vault = self.vault()
        for name in self.fnox_bootstrap_secrets:
            console.cmd(f"fnox get {name}")
            if vault.has_value(name):
                console.success(f"{name}: cached")
            else:
                console.error(f"{name} not stored — run `bake setup-fnox`")
