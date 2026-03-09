from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import Field

from bake import Bakebook, GroupKwargs, command, console
from bakelib.refreshable_cache import ChainedCache, KeyringCache, MemoryCache, RefreshableCache

if TYPE_CHECKING:
    from tenacity.stop import StopBaseT
    from tenacity.wait import WaitBaseT

SECRET_GROUP = "secret"
DEFAULT_SECRET_BACKENDS: list[type[RefreshableCache]] = [MemoryCache, KeyringCache]

secret_backends_type = Annotated[list[type[RefreshableCache]], Field(exclude=True, repr=False)]


def null_fetch_fn() -> str | None:
    return None


class SecretUtils(Bakebook):
    secret_backends: secret_backends_type = DEFAULT_SECRET_BACKENDS

    def get_secret_keys(self) -> set[str]:
        return set()

    def get_group_kwargs(self) -> dict[str, GroupKwargs]:
        return {SECRET_GROUP: GroupKwargs(help="Manage cached secrets")}

    def get_secret_namespace(self) -> str:
        return "bakebook"

    def _get_fetch_fn(self, key: str) -> Callable[[], str | None]:
        _ = key

        return null_fetch_fn

    def get_secret_cache(
        self,
        key: str,
        *,
        ttl: float | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> ChainedCache[str | None]:
        """Get a ChainedCache instance for a secret key."""
        return ChainedCache(
            backends=self.secret_backends,
            namespace=self.get_secret_namespace(),
            key=key,
            fetch_fn=self._get_fetch_fn(key),
            ttl=ttl,
            stop=stop,
            wait=wait,
            cached_type=cached_type,
        )

    @command(name="list", group_name=SECRET_GROUP)
    def secret_list(self) -> None:
        """List all tracked keys with their cache status."""
        if not self.get_secret_keys():
            console.echo("No tracked secrets.")
            return

        console.echo(f"Tracked secrets (namespace: {self.get_secret_namespace()}):")
        for key in sorted(self.get_secret_keys()):
            cache = self.get_secret_cache(key)
            entry = cache._get_entry()
            status = "[green]cached[/green]" if entry else "[dim]not cached[/dim]"
            console.echo(f"  {key}: {status}")

    def get_secret(self, key: str) -> str | None:
        cache = self.get_secret_cache(key)
        return cache.get_value()

    def set_secret(self, key: str, value: str) -> None:
        cache = self.get_secret_cache(key)
        cache.set(value)

    def del_secret(self, key: str) -> None:
        cache = self.get_secret_cache(key)
        cache.delete()

    def refresh_secret(self, key: str) -> None:
        cache = self.get_secret_cache(key)
        cache.refresh()

    @command(name="get", group_name=SECRET_GROUP)
    def secret_get(
        self,
        key: Annotated[str, typer.Argument(help="Secret key")],
    ) -> None:
        """Get a cached secret value."""
        value = self.get_secret(key)
        if value is None:
            console.error(f"Secret '{key}' not found.")
            raise typer.Exit(1)
        console.echo(value)

    @command(name="set", group_name=SECRET_GROUP)
    def secret_set(
        self,
        key: Annotated[str, typer.Argument(help="Secret key")],
        value: Annotated[str, typer.Argument(help="Secret value")],
    ) -> None:
        """Set a secret value in cache."""
        if key not in self.get_secret_keys():
            console.warning(f"Key '{key}' is not registered. It will not persist across sessions.")
        self.set_secret(key, value)
        console.success(f"Secret '{key}' set.")

    @command(name="del", group_name=SECRET_GROUP)
    def secret_del(
        self,
        key: Annotated[str | None, typer.Argument(help="Secret key")] = None,
    ) -> None:
        """Delete secret(s) from cache.

        If no key provided, deletes all tracked secrets.
        """
        if key is None:
            # Delete all tracked secrets
            for k in self.get_secret_keys():
                self.del_secret(k)
                console.echo(f"Deleted: {k}")
            console.success("All tracked secrets deleted.")
            return

        # Delete specific key
        self.del_secret(key)
        console.success(f"Secret '{key}' deleted.")

    @command(name="refresh", group_name=SECRET_GROUP)
    def secret_refresh(
        self,
        key: Annotated[str | None, typer.Argument(help="Secret key")] = None,
    ) -> None:
        """Refresh secret(s) by clearing cache and fetching fresh value(s).

        If no key provided, refreshes all tracked secrets.
        """
        if key is None:
            # Refresh all tracked secrets
            for k in self.get_secret_keys():
                self.refresh_secret(k)
                console.echo(f"Refreshed: {k}")
            console.success("All tracked secrets refreshed.")
            return

        # Refresh specific key
        self.refresh_secret(key)
        console.success(f"Secret '{key}' refreshed.")
