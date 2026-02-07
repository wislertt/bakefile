import shutil
import subprocess
from contextlib import contextmanager
from typing import Annotated, Literal, cast, get_args

import typer

from bake import Context, console

from .lib import BaseLibSpace, PublishResult
from .rust import RustSpace

CratesRegistry = Literal["crates"]


class RustLibSpace(RustSpace, BaseLibSpace):
    @property
    def _version_schema(self) -> str | None:
        return "standard-base-prerelease-post-dev"

    @property
    def _version_output_format(self) -> str | None:
        return "semver"

    def _validate_registry(self, registry: str) -> CratesRegistry:
        valid_registries = get_args(CratesRegistry)
        if registry not in valid_registries:
            console.error(f"Invalid registry: {registry!r}. Expected one of {valid_registries}.")
            raise typer.Exit(1)
        return cast(CratesRegistry, registry)

    def _get_publish_token_from_remote(self, registry: str) -> str | None:
        self._validate_registry(registry)
        return None

    def _build_for_publish(self, ctx: Context):
        pass

    def _publish_with_token(self, ctx: Context, token: str | None, registry: str) -> PublishResult:
        self._validate_registry(registry)
        dry_run_flag = "" if token is not None else "--dry-run "
        is_dry_run = token is None

        env: dict[str, str] = {}
        if token is not None:
            env["CARGO_REGISTRY_TOKEN"] = token

        result = ctx.run(
            f"cargo publish --allow-dirty {dry_run_flag}",
            stream=True,
            env=env,
            check=False,
        )

        return PublishResult(
            result=result,
            is_dry_run=is_dry_run,
            is_auth_failed=self._is_auth_failure(result),
        )

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        auth_error_messages = ["status 403 Forbidden", "status 401 Unauthorized"]
        return result.returncode != 0 and any(msg in result.stderr for msg in auth_error_messages)

    @contextmanager
    def _version_bump_context(self, ctx: Context, version: str):
        original_version = self.current_version(ctx)
        self._set_version(ctx, version)
        try:
            yield
        finally:
            self._set_version(ctx, original_version)

    def _pre_publish_cleanup(self, _ctx: Context):
        shutil.rmtree("target/package", ignore_errors=True)

    def publish(
        self,
        ctx: Context,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry (crates)")] = "crates",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        self._validate_registry(registry)
        return super().publish(ctx=ctx, registry=registry, token=token, version=version)
