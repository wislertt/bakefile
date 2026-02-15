import shutil
import subprocess
from typing import Annotated, Literal, cast, get_args

import typer

from bake import console

from .lib import BaseLibSpace, PublishResult
from .rust import RustSpace

CratesRegistry = Literal["crates"]


class RustLibSpace(RustSpace, BaseLibSpace):
    def _validate_registry(self, registry: str) -> CratesRegistry:
        valid_registries = get_args(CratesRegistry)
        if registry not in valid_registries:
            console.error(f"Invalid registry: {registry!r}. Expected one of {valid_registries}.")
            raise typer.Exit(1)
        return cast(CratesRegistry, registry)

    def _get_publish_token_from_remote(self, registry: str) -> str | None:
        self._validate_registry(registry)
        return None

    def _build_for_publish(self):
        # cargo publish handles compilation automatically
        pass

    def _publish_with_token(self, token: str | None, registry: str) -> PublishResult:
        self._validate_registry(registry)
        dry_run_flag = "" if token is not None else "--dry-run "

        env: dict[str, str] = {}
        if token is not None:
            env["CARGO_REGISTRY_TOKEN"] = token

        result = self.ctx.run(
            f"cargo publish --allow-dirty {dry_run_flag}",
            stream=True,
            env=env,
            check=False,
        )

        return self._determine_publish_result(token=token, result=result)

    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        already_exists_msg = "already exists on crates.io"
        return result.returncode != 0 and already_exists_msg in result.stderr

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        auth_error_messages = ["status 403 Forbidden", "status 401 Unauthorized"]
        return result.returncode != 0 and any(msg in result.stderr for msg in auth_error_messages)

    def _pre_publish_setup(self):
        shutil.rmtree("target/package", ignore_errors=True)

    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry (crates)")] = "crates",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        self._validate_registry(registry)
        return super().publish(registry=registry, token=token, version=version)
