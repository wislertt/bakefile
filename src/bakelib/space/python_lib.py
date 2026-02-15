import shutil
import subprocess
from typing import Annotated, Literal, cast, get_args

import typer

from bake import console

from .lib import BaseLibSpace, PublishResult
from .python import PythonSpace

PyPIRegistry = Literal["test-pypi", "pypi"]


class PythonLibSpace(PythonSpace, BaseLibSpace):
    def _validate_registry(self, registry: str) -> PyPIRegistry:
        valid_registries = get_args(PyPIRegistry)
        if registry not in valid_registries:
            console.error(f"Invalid registry: {registry!r}. Expected one of {valid_registries}.")
            raise typer.Exit(1)
        return cast(PyPIRegistry, registry)

    def _get_publish_token_from_remote(self, registry: str) -> str | None:
        self._validate_registry(registry)
        return None

    def _build_for_publish(self):
        self.ctx.run("uv build")

    def _publish_with_token(self, token: str | None, registry: str) -> PublishResult:
        pypi_registry = self._validate_registry(registry)
        index_flag = f"--index {pypi_registry} " if pypi_registry == "test-pypi" else ""
        dry_run_flag = "" if token is not None else "--dry-run "

        env: dict[str, str] = {
            "UV_PUBLISH_TOKEN": token if token is not None else self._dummy_publish_token
        }

        result = self.ctx.run(
            f"uv publish {dry_run_flag}{index_flag}",
            stream=True,
            env=env,
            check=False,
        )

        return self._determine_publish_result(token=token, result=result)

    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        # Success case (returncode == 0)
        if result.returncode == 0 and "already exists, skipping" in result.stderr:
            return True

        # Error cases (returncode != 0)
        error_messages = [
            "Local file and index file do not match",
            "File already exists",
        ]
        return result.returncode != 0 and any(msg in result.stderr for msg in error_messages)

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        auth_error_message = "403 Invalid or non-existent authentication information"
        return result.returncode != 0 and auth_error_message in result.stderr

    def _pre_publish_setup(self):
        shutil.rmtree("dist", ignore_errors=True)

    def publish(
        self,
        *,
        registry: Annotated[
            str, typer.Option(help="Publish registry (test-pypi or pypi)")
        ] = "test-pypi",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        self._validate_registry(registry)
        return super().publish(registry=registry, token=token, version=version)
