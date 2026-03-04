import shutil
import subprocess
from typing import TYPE_CHECKING, Literal, get_args

from . import Publisher

if TYPE_CHECKING:
    from bake.cli.common.context import Context

PyPIRegistry = Literal["test-pypi", "pypi"]


class PyPIPublisher(Publisher):
    """Publisher for PyPI (Python Package Index)."""

    valid_registries: tuple[str, ...] = get_args(PyPIRegistry)

    def _get_publish_token_from_remote(self) -> str | None:
        return None

    def _build_for_publish(self):
        self.ctx.run("uv build")

    def _setup_token_env(self, env: dict[str, str], token: str) -> None:
        env["UV_PUBLISH_TOKEN"] = token

    def _execute_publish_command(
        self, env: dict[str, str], token: str | None
    ) -> subprocess.CompletedProcess[str]:
        index_flag = f"--index {self.registry} " if self.registry == "test-pypi" else ""
        dry_run_flag = "" if token is not None else "--dry-run "
        command = f"uv publish {dry_run_flag}{index_flag}"

        return self.ctx.run(command, stream=True, env=env, check=False)

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

    @classmethod
    def _pre_publish_setup(cls, ctx: "Context") -> None:
        _ = ctx
        shutil.rmtree("dist", ignore_errors=True)
