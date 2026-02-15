import subprocess
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

import typer
from pydantic import SecretStr
from tenacity import stop_after_attempt

from bake import command, console
from bakelib.refreshable_cache import ChainedCache, KeyringCache, NullCache

from .base import BaseSpace


class PublishStatus(Enum):
    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    DRY_RUN = "dry_run"
    AUTH_FAILED = "auth_failed"
    ERROR = "error"
    OTHER = "other"


@dataclass
class PublishResult:
    result: subprocess.CompletedProcess[str] | None
    status: PublishStatus


class BaseLibSpace(BaseSpace):
    bake_publish_token: SecretStr | None = None
    _dummy_publish_token: str = "dummy-token-for-dry-run"

    @abstractmethod
    def _validate_registry(self, registry: str) -> str: ...

    @abstractmethod
    def _get_publish_token_from_remote(self, registry: str) -> str | None: ...

    @abstractmethod
    def _build_for_publish(self): ...

    @abstractmethod
    def _publish_with_token(self, token: str | None, registry: str) -> PublishResult: ...

    def _get_cached_publish_token(
        self, token: str | None, registry: str
    ) -> ChainedCache[str | None]:
        token_from_local = self._get_token_from_local(token)
        key = f"publish-token-{registry}"

        def get_publish_token() -> str | None:
            return token_from_local or self._get_publish_token_from_remote(registry)

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

    @abstractmethod
    def _pre_publish_setup(self): ...

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        _ = result
        self._method_not_available("_is_auth_failure")

    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        _ = result
        self._method_not_available("_is_already_exists_error")

    def _determine_publish_result(
        self, token: str | None, result: subprocess.CompletedProcess[str]
    ) -> PublishResult:
        if token is None:
            status = PublishStatus.DRY_RUN
        elif self._is_already_exists_error(result):
            status = PublishStatus.ALREADY_EXISTS
        elif self._is_auth_failure(result):
            status = PublishStatus.AUTH_FAILED
        elif result.returncode == 0:
            status = PublishStatus.SUCCESS
        else:
            status = PublishStatus.ERROR

        return PublishResult(result=result, status=status)

    @command(help="Build and publish the package")
    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry")] = "default",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        cached_publish_token = self._get_cached_publish_token(token=token, registry=registry)

        console.start(f"Publishing to [bold cyan]{registry}[/bold cyan]")
        self._pre_publish_setup()

        with self._version_bump_context(version):
            self._build_for_publish()
            publish_result = self._execute_publish(
                cached_publish_token=cached_publish_token, registry=registry
            )

        self._handle_publish_result(publish_result=publish_result)

    def _execute_publish(
        self, cached_publish_token: ChainedCache[str | None], registry: str
    ) -> PublishResult:
        @cached_publish_token.catch_refresh
        def _publish() -> PublishResult:
            token_value = cached_publish_token.get_value()
            publish_result = self._publish_with_token(token=token_value, registry=registry)

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

        match publish_result.status:
            case PublishStatus.SUCCESS:
                console.success("Publish succeeded!")
            case PublishStatus.ALREADY_EXISTS:
                console.warning("Version already exists, skipping publish.")
            case PublishStatus.DRY_RUN:
                console.warning(
                    "This was a dry-run. To actually publish, "
                    "set the BAKE_PUBLISH_TOKEN environment variable"
                )
            case PublishStatus.AUTH_FAILED:
                console.error("Authentication failed. Please check your publish token.")
                raise typer.Exit(1)
            case PublishStatus.ERROR:
                result = publish_result.result
                returncode = result.returncode if result else "unknown"
                console.error(f"Publish failed with unexpected error. Return code: {returncode}")
                raise typer.Exit(1)
            case _:
                console.error(f"Unexpected publish status: {publish_result.status}")
                raise typer.Exit(1)
