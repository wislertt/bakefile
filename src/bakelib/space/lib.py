from abc import abstractmethod
from typing import TYPE_CHECKING, Annotated

import typer
from pydantic import SecretStr
from tenacity import stop_after_attempt

from bake import command, console
from bakelib.publisher import PublishResult, PublishStatus
from bakelib.refreshable_cache import ChainedCache, KeyringCache, NullCache

from .base import BaseSpace
from .utils import print_subprocess_output

if TYPE_CHECKING:
    from bakelib.publisher import Publisher


class BaseLibSpace(BaseSpace):
    bake_publish_token: SecretStr | None = None

    @abstractmethod
    def get_publisher(self, registry: str) -> "Publisher":
        """Return the Publisher instance for the given registry after validation."""
        ...

    def _get_cached_publish_token(
        self, token: str | None, registry: str, publisher: "Publisher"
    ) -> ChainedCache[str | None]:
        token_from_local = self._get_token_from_local(token)
        key = f"publish-token-{registry}"

        def get_publish_token() -> str | None:
            return token_from_local or publisher._get_publish_token_from_remote()

        stop = stop_after_attempt(1) if token_from_local else None

        cached_publish_token = ChainedCache(
            backends=[KeyringCache, NullCache],
            namespace=self._package_name,
            key=key,
            fetch_fn=get_publish_token,
            stop=stop,
        )

        if token_from_local is not None:
            cached_publish_token.set(token_from_local)

        return cached_publish_token

    def _get_token_from_local(self, token: str | None) -> str | None:
        if token:
            return token

        if self.bake_publish_token:
            return self.bake_publish_token.get_secret_value()

        return None

    @command(help="Build and publish the package")
    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry")] = "default",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        publisher = self.get_publisher(registry)
        cached_publish_token = self._get_cached_publish_token(
            token=token, registry=registry, publisher=publisher
        )

        console.start(f"Publishing to [bold cyan]{registry}[/bold cyan]")
        publisher._pre_publish_setup()

        with self._version_bump_context(version):
            publisher._build_for_publish()
            publish_result = self._execute_publish(
                publisher=publisher, cached_publish_token=cached_publish_token
            )

        self._handle_publish_result(publish_result=publish_result)

    def _execute_publish(
        self, publisher: "Publisher", cached_publish_token: ChainedCache[str | None]
    ) -> PublishResult:
        @cached_publish_token.catch_refresh
        def _publish() -> PublishResult:
            token_value = cached_publish_token.get_value()
            publish_result = publisher._publish_with_token(token=token_value)

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
