import shutil
import subprocess
from typing import TYPE_CHECKING, Literal, get_args

from . import Publisher

if TYPE_CHECKING:
    from bake.cli.common.context import Context

CratesRegistry = Literal["crates"]


class CratesPublisher(Publisher):
    """Publisher for crates.io."""

    valid_registries: tuple[str, ...] = get_args(CratesRegistry)

    def _get_publish_token_from_remote(self) -> str | None:
        return None

    def _build_for_publish(self, ctx: "Context"):
        # cargo publish handles compilation automatically
        _ = ctx

    def _setup_token_env(self, env: dict[str, str], token: str) -> None:
        env["CARGO_REGISTRY_TOKEN"] = token

    def _execute_publish_command(
        self, ctx: "Context", env: dict[str, str], token: str | None
    ) -> subprocess.CompletedProcess[str]:
        dry_run_flag = "" if token is not None else "--dry-run "
        command = f"cargo publish --allow-dirty {dry_run_flag}"

        return ctx.run(command, stream=True, env=env, check=False, capture_output=True)

    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        already_exists_msg = "already exists on crates.io"
        return result.returncode != 0 and already_exists_msg in result.stderr

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        auth_error_messages = ["status 403 Forbidden", "status 401 Unauthorized"]
        return result.returncode != 0 and any(msg in result.stderr for msg in auth_error_messages)

    @classmethod
    def _pre_publish_setup(cls, ctx: "Context") -> None:
        _ = ctx
        shutil.rmtree("target/package", ignore_errors=True)
