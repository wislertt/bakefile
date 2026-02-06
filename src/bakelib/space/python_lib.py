import shutil
import subprocess
from contextlib import contextmanager
from typing import Annotated, Literal, cast, get_args

import typer

from bake import Context

from .lib import BaseLibSpace, PublishResult
from .python import PythonSpace

PyPIRegistry = Literal["testpypi", "pypi"]


class PythonLibSpace(PythonSpace, BaseLibSpace):
    @property
    def _version_schema(self) -> str | None:
        return "standard-base-prerelease-post-dev"

    @property
    def _version_output_format(self) -> str | None:
        return "pep440"

    def _validate_pypi_registry(self, registry: str) -> PyPIRegistry:
        valid_indices = get_args(PyPIRegistry)
        if registry not in valid_indices:
            raise ValueError(f"Invalid registry: {registry!r}. Expected one of {valid_indices}.")
        return cast(PyPIRegistry, registry)

    def _get_publish_token_from_remote(self, registry: str) -> str | None:
        pypi_registry = self._validate_pypi_registry(registry)
        _ = pypi_registry
        return None

    def _build_for_publish(self, ctx: Context):
        ctx.run("uv build")

    def _publish_with_token(self, ctx: Context, token: str | None, registry: str) -> PublishResult:
        pypi_registry = self._validate_pypi_registry(registry)
        index_flag = f"--index {pypi_registry} " if pypi_registry == "testpypi" else ""
        dry_run_flag = "" if token is not None else "--dry-run "
        is_dry_run = token is None

        env: dict[str, str] = {
            "UV_PUBLISH_TOKEN": token if token is not None else self._dummy_publish_token
        }

        result = ctx.run(
            f"uv publish {dry_run_flag}{index_flag}",
            stream=True,
            env=env,
            check=False,
        )

        return PublishResult(result=result, is_dry_run=is_dry_run, is_auth_failed=False)

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        auth_error_message = "403 Invalid or non-existent authentication information"
        return result.returncode != 0 and auth_error_message in result.stderr

    @contextmanager
    def _version_bump_context(self, ctx: Context, version: str):
        original_version = self.current_version(ctx)
        ctx.run(f"uv version {version}")
        try:
            yield
        finally:
            ctx.run(f"uv version {original_version}")

    def _pre_publish_cleanup(self, _ctx: Context):
        shutil.rmtree("dist", ignore_errors=True)

    def publish(
        self,
        ctx: Context,
        *,
        registry: Annotated[
            str, typer.Option(help="Publish registry (testpypi or pypi)")
        ] = "testpypi",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        self._validate_pypi_registry(registry)
        return super().publish(ctx=ctx, registry=registry, token=token, version=version)
