import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from bake.cli.common.context import Context


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


class Publisher(ABC):
    """Abstract base class for platform-specific publishing logic."""

    valid_registries: tuple[str, ...]

    def __init__(self, registry: str) -> None:
        from bake import console

        super().__init__()
        if registry not in self.valid_registries:
            console.error(
                f"Invalid registry: {registry!r}. Expected one of {self.valid_registries}."
            )
            raise typer.Exit(1)
        self.registry = registry
        self._dummy_publish_token: str = "dummy-token-for-dry-run"

    @abstractmethod
    def _get_publish_token_from_remote(self) -> str | None:
        """Get the publish token from a remote source."""
        ...

    @abstractmethod
    def _build_for_publish(self, ctx: "Context"):
        """Build the package for publishing."""
        ...

    def _publish_with_token(self, ctx: "Context", token: str | None) -> PublishResult:
        """Publish with the given token."""
        env: dict[str, str] = {}
        # Convert empty string to None, then use dummy token for both None and empty string cases
        normalized_token = token if token else None
        effective_token = (
            normalized_token if normalized_token is not None else self._dummy_publish_token
        )
        self._setup_token_env(env, effective_token)

        result = self._execute_publish_command(ctx, env, effective_token)

        return self._determine_publish_result(token=token, result=result)

    @abstractmethod
    def _setup_token_env(self, env: dict[str, str], token: str) -> None:
        """Set up the token in the environment."""
        ...

    @abstractmethod
    def _execute_publish_command(
        self, ctx: "Context", env: dict[str, str], token: str | None
    ) -> subprocess.CompletedProcess[str]:
        """Execute the publish command."""
        ...

    @abstractmethod
    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        """Check if the result indicates the package already exists."""
        ...

    @abstractmethod
    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        """Check if the result indicates an authentication failure."""
        ...

    @classmethod
    def _pre_publish_setup(cls, ctx: "Context") -> None:
        """Perform setup before publishing.

        Subclasses must override this to provide platform-specific setup.
        """
        raise NotImplementedError(f"{cls.__name__}._pre_publish_setup() must be overridden")

    def _is_dry_run(self, token: str | None, result: subprocess.CompletedProcess[str]) -> bool:
        _ = result
        return not token

    def _determine_publish_result(
        self, token: str | None, result: subprocess.CompletedProcess[str]
    ) -> PublishResult:
        """Determine the publish result status from the token and result."""
        if self._is_dry_run(token, result):
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
