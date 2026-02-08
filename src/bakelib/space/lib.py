import subprocess
from abc import abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated

import typer
from pydantic import SecretStr
from tenacity import stop_after_attempt

from bake import command, console
from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import ChainedCache, KeyringCache, NullCache

from .base import BaseSpace, ToolInfo
from .utils import CARGO_BIN, PlatformType, get_expected_paths, setup_rustup, setup_zerv


@dataclass
class PublishResult:
    result: subprocess.CompletedProcess[str] | None
    is_dry_run: bool
    is_auth_failed: bool


class BaseLibSpace(BaseSpace):
    bake_publish_token: SecretStr | None = None
    _dummy_publish_token: str = "dummy-token-for-dry-run"

    def setup_tools(self, platform: PlatformType) -> None:
        _ = platform
        super().setup_tools(platform=platform)
        setup_rustup(self.ctx)
        setup_zerv(self.ctx)

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
        namespace = self.package_name()

        def get_publish_token() -> str | None:
            return token_from_local or self._get_publish_token_from_remote(registry)

        stop = stop_after_attempt(1) if token_from_local else None

        cached_publish_token = ChainedCache(
            backends=[KeyringCache, NullCache],
            namespace=namespace,
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

    @contextmanager
    @abstractmethod
    def _version_bump_context(self, version: str): ...

    @abstractmethod
    def _pre_publish_cleanup(self): ...

    @property
    def _version_schema(self) -> str | None:
        return None

    @property
    def _version_output_format(self) -> str | None:
        return None

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        return result.returncode != 0

    def _determine_version(self, version: str | None) -> str:
        return version if version else self.zerv_versioning()

    @command(help="Build and publish the package")
    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry")] = "default",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        cached_publish_token = self._get_cached_publish_token(token=token, registry=registry)
        version = self._determine_version(version)

        console.start(
            f"Publishing [bold green]{version}[/bold green] "
            f"[dim]({self._version_output_format})[/dim] to [bold cyan]{registry}[/bold cyan]"
        )
        self._pre_publish_cleanup()

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

            if publish_result.result is not None and self._is_auth_failure(publish_result.result):
                raise cached_publish_token.RefreshNeededError

            return publish_result

        try:
            return _publish()
        except cached_publish_token.RefreshNeededError:
            return PublishResult(result=None, is_dry_run=False, is_auth_failed=True)

    def _handle_publish_result(self, publish_result: PublishResult) -> None:
        if publish_result.is_auth_failed:
            console.error("Authentication failed. Please check your publish token.")
            raise typer.Exit(1)

        if publish_result.is_dry_run and not self.ctx.dry_run:
            console.warning(
                "This was a dry-run. To actually publish, "
                "set the BAKE_PUBLISH_TOKEN environment variable"
            )

    def zerv_versioning(
        self, *, schema: str | None = None, output_format: str | None = None
    ) -> str:
        schema = schema if schema is not None else self._version_schema
        output_format = output_format if output_format is not None else self._version_output_format

        schema_flag = f" --schema {schema}" if schema else ""
        output_format_flag = f" --output-format {output_format}" if output_format else ""

        result = self.ctx.run(f"zerv flow{schema_flag}{output_format_flag}", dry_run=False)
        return strip_ansi(result.stdout.strip())

    def _get_tools(self) -> dict[str, ToolInfo]:
        tools = super()._get_tools()
        tools["zerv"] = ToolInfo(expected_paths=get_expected_paths("zerv", {CARGO_BIN}))
        return tools
