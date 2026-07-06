from abc import abstractmethod
from typing import TYPE_CHECKING, Annotated

import typer
from pydantic import SecretStr
from tenacity import stop_after_attempt

from bake import command, console
from bakelib.publisher import PublishResult, PublishStatus
from bakelib.refreshable_cache import FetchFn, NullFetchFn, RefreshableCache
from bakelib.utils.secret import SecretUtils

from .base import BaseSpace
from .params import PublishTokenOption, PublishVersionOption
from .utils import print_subprocess_output

if TYPE_CHECKING:
    from bakelib.publisher import Publisher

PUBLISH_TOKEN_KEY_PREFIX = "publish-token-"


class BaseLibSpace(SecretUtils[str | None], BaseSpace):
    bake_publish_token: SecretStr | None = None
    _publisher: "Publisher | None" = None

    def get_secret_fetch_fns(self) -> tuple[FetchFn[str | None], ...]:
        publish_fns = tuple(
            NullFetchFn[str | None](f"{PUBLISH_TOKEN_KEY_PREFIX}{r}")
            for r in self.get_publish_registries()
        )
        return (*super().get_secret_fetch_fns(), *publish_fns)

    def get_secret_namespace(self) -> str:
        return self._package_name

    @abstractmethod
    def get_publish_registries(self) -> set[str]:
        """Return the set of valid publish registries for this library."""
        ...

    @abstractmethod
    def get_publisher(self, registry: str) -> "Publisher":
        """Return the Publisher instance for the given registry after validation."""
        ...

    def _get_publish_token(self) -> str | None:
        if self.bake_publish_token:
            return self.bake_publish_token.get_secret_value()
        if self._publisher:
            return self._publisher._get_publish_token_from_remote()
        return None

    def _get_cached_publish_token(
        self, token: str | None, registry: str
    ) -> RefreshableCache[str | None]:
        if token:
            self.bake_publish_token = SecretStr(token)

        key = f"{PUBLISH_TOKEN_KEY_PREFIX}{registry}"
        stop = stop_after_attempt(1) if self.bake_publish_token else None

        vault = self.vault()
        if key in vault and stop is not None:
            vault.unregister(key)
        if key not in vault:
            vault.register(key, fetch_fn=self._get_publish_token, stop=stop)

        cached_publish_token = vault.cache(key)

        if self.bake_publish_token is not None:
            cached_publish_token.set(self.bake_publish_token.get_secret_value())

        return cached_publish_token

    @command(help="Build and publish the package")
    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry")] = "default",
        token: PublishTokenOption = None,
        version: PublishVersionOption = None,
    ):
        self._publisher = self.get_publisher(registry)
        cached_publish_token = self._get_cached_publish_token(token=token, registry=registry)

        console.start(f"Publishing to [bold cyan]{registry}[/bold cyan]")
        self._pre_publish_setup()

        with self._version_bump_context(version):
            self._publisher._build_for_publish()
            publish_result = self._execute_publish(cached_publish_token=cached_publish_token)

        self._handle_publish_result(publish_result=publish_result)

    def _pre_publish_setup(self) -> None:
        """Default pre-publish setup - delegates to publisher class method.

        Subclasses can override this to add custom setup before/after
        calling the publisher's setup.
        """
        if self._publisher is None:
            raise ValueError("_publisher is not set. Call `get_publisher` first.")
        self._publisher._pre_publish_setup(self.ctx)

    def _execute_publish(
        self,
        cached_publish_token: RefreshableCache[str | None],
    ) -> PublishResult:

        @cached_publish_token.catch_refresh
        def _publish() -> PublishResult:
            if self._publisher is None:
                raise ValueError("_publisher is not set. Call `get_publisher` first.")

            token_value = cached_publish_token.get_value()
            publish_result = self._publisher._publish_with_token(token=token_value)

            if publish_result.status == PublishStatus.AUTH_FAILED:
                raise cached_publish_token.RefreshNeededError

            return publish_result

        try:
            return _publish()
        except cached_publish_token.RefreshNeededError:
            return PublishResult(result=None, status=PublishStatus.AUTH_FAILED)

    def _handle_publish_result(self, publish_result: PublishResult) -> None:
        if self.ctx.dry_run:
            return

        returncode_display = (
            publish_result.result.returncode if publish_result.result else "unknown"
        )

        match publish_result.status:
            case PublishStatus.SUCCESS:
                console.success("Publish succeeded!")
            case PublishStatus.ALREADY_EXISTS:
                console.warning("Version already exists, skipping publish.")
            case PublishStatus.DRY_RUN:
                console.warning(
                    "This was a dry-run. To actually publish, "
                    "set the `BAKE_PUBLISH_TOKEN` environment variable"
                )
            case PublishStatus.AUTH_FAILED:
                console.error("Authentication failed. Please check your publish token.")
                raise typer.Exit(1)
            case PublishStatus.ERROR:
                console.error(
                    f"Publish failed with unexpected error. Return code: {returncode_display}"
                )
                print_subprocess_output(publish_result.result)
                raise typer.Exit(1)
            case _:
                console.error(
                    f"Unexpected publish status: {publish_result.status}. "
                    f"Return code: {returncode_display}"
                )
                print_subprocess_output(publish_result.result)
                raise typer.Exit(1)
