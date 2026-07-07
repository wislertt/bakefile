from typing import Annotated, Any, ClassVar, Generic, TypeVar, cast

import typer

from bake import Bakebook, GroupKwargs, command, console
from bakelib.refreshable_cache import (
    FetchFn,
    RefreshableCacheRegistry,
    SecretUtilsKeyringCacheRegistry,
)

SECRET_GROUP = "secret"

T = TypeVar("T")


class SecretUtils(Bakebook, Generic[T]):
    _cache_registry_cls: ClassVar[type[RefreshableCacheRegistry[Any]]] = (
        SecretUtilsKeyringCacheRegistry[T]
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vault: RefreshableCacheRegistry[T] | None = None

    def get_secret_fetch_fns(self) -> tuple[FetchFn[T], ...]:
        return ()

    def get_secret_namespace(self) -> str:
        return "bakebook"

    def vault(self) -> RefreshableCacheRegistry[T]:
        if self._vault is None:
            self._vault = self._cache_registry_cls(namespace=self.get_secret_namespace())
            for fetch_fn in self.get_secret_fetch_fns():
                self._vault.register(fetch_fn.key, fetch_fn=fetch_fn)
        return self._vault

    def get_group_kwargs(self) -> dict[str, GroupKwargs]:
        group_kwargs = super().get_group_kwargs()
        group_kwargs[SECRET_GROUP] = GroupKwargs(help="Manage cached secrets")
        return group_kwargs

    @command(
        name="list",
        group_name=SECRET_GROUP,
        help="List all tracked secret keys with cache status",
    )
    def secret_list(self) -> None:
        if not self.vault().keys():
            console.echo("No tracked secrets.")
            return

        console.echo(f"Tracked secrets (namespace: {self.vault().namespace}):")
        for key in sorted(self.vault().keys()):
            status = (
                "[green]cached[/green]" if self.vault().is_cached(key) else "[dim]not cached[/dim]"
            )
            console.echo(f"  {key}: {status}")

    def get_secret(self, key: str) -> T:
        return self.vault().cache(key).get_value()

    def set_secret(self, key: str, value: str) -> None:
        self.vault().cache(key).set(cast("T", value))

    def del_secret(self, key: str) -> None:
        self.vault().cache(key).delete()

    def refresh_secret(self, key: str) -> None:
        self.vault().cache(key).refresh()

    def _require_tracked_key(self, key: str) -> None:
        if key not in self.vault():
            console.error(
                f"Secret key '{key}' not tracked. Run `bake secret list` to see tracked keys."
            )
            raise typer.Exit(1)

    @command(name="get", group_name=SECRET_GROUP, help="Get a cached secret value")
    def secret_get(
        self,
        key: Annotated[str, typer.Argument(help="Secret key")],
    ) -> None:
        self._require_tracked_key(key)
        value = self.get_secret(key)
        if value is None:
            console.error(f"Secret '{key}' not found.")
            raise typer.Exit(1)
        console.echo(value)

    @command(name="set", group_name=SECRET_GROUP, help="Set a secret value in cache")
    def secret_set(
        self,
        key: Annotated[str, typer.Argument(help="Secret key")],
        value: Annotated[str, typer.Argument(help="Secret value")],
    ) -> None:
        self._require_tracked_key(key)
        self.set_secret(key, value)
        console.success(f"Secret '{key}' set.")

    @command(name="del", group_name=SECRET_GROUP, help="Delete secret(s) from cache")
    def secret_del(
        self,
        key: Annotated[str | None, typer.Argument(help="Secret key")] = None,
    ) -> None:
        if key is None:
            self.vault().delete_all()
            console.success("All tracked secrets deleted.")
            return

        self._require_tracked_key(key)
        self.del_secret(key)
        console.success(f"Secret '{key}' deleted.")

    @command(
        name="refresh", group_name=SECRET_GROUP, help="Refresh secret(s) by fetching fresh value(s)"
    )
    def secret_refresh(
        self,
        key: Annotated[str | None, typer.Argument(help="Secret key")] = None,
    ) -> None:
        if key is None:
            self.vault().refresh_all()
            console.success("All tracked secrets refreshed.")
            return

        self._require_tracked_key(key)
        self.refresh_secret(key)
        console.success(f"Secret '{key}' refreshed.")
