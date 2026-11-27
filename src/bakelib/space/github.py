from datetime import date
from pathlib import Path
from typing import ClassVar, Literal

from bake import Context
from bakelib.managed_content import ManagedFile
from bakelib.space import BaseSpace
from bakelib.utils import GitHubActionsEnvVars

from .base import local_mise_tools
from .migration import Migration

ACTIONS_UP_MIN_AGE_DAYS = 3


class RemoveActionlint(Migration):
    expires = date(2027, 2, 25)
    description = "Remove actionlint from the project's mise config, replaced by jactionlint"

    def check(self, ctx: Context) -> bool:
        return "actionlint" in local_mise_tools(ctx)

    def apply(self, ctx: Context) -> None:
        ctx.run("mise unuse actionlint")


class GitHubActionsTools(GitHubActionsEnvVars, BaseSpace):
    # default is actionlint plus zizmor's regular audits; None lets .github/jactionlint.yaml decide
    jactionlint_profile: ClassVar[Literal["correctness", "default", "pedantic"] | None] = "default"

    def _get_mise_tools(self) -> set[str]:
        return super()._get_mise_tools() | {"jactionlint", "npm:actions-up", "shellcheck"}

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["jactionlint"] = None
        tools["actions-up"] = None
        # jactionlint skips run: scripts without shellcheck, unlike CI runners
        tools["shellcheck"] = None
        return tools

    def _get_migrations(self) -> dict[str, Migration]:
        return {**super()._get_migrations(), "remove-actionlint": RemoveActionlint()}

    def _lint_fast(self) -> None:
        super()._lint_fast()
        self._jactionlint()

    def _lint_slow(self) -> None:
        super()._lint_slow()
        self._jactionlint("--online")

    def _jactionlint(self, *flags: str) -> None:
        # --profile overrides the config file's profile, so pass it only when set
        profile = ["--profile", self.jactionlint_profile] if self.jactionlint_profile else []
        self.ctx.run(" ".join(["jactionlint", *profile, *flags]))

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {
            **super()._get_managed_files(),
            ".github/renovate.json5": ManagedFile(__package__, "renovate.json5"),
            ".github/workflows/security.yml": ManagedFile(__package__, "security.yml"),
        }

    def _actions_up(self):
        # Separate method for overriding - subclasses can customize the command
        self.ctx.run(f"actions-up --yes --min-age {ACTIONS_UP_MIN_AGE_DAYS}")

    def _update_project(self) -> None:
        super()._update_project()
        self._actions_up()


class ZervGitHubActionsTools(GitHubActionsTools):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {
            **super()._get_managed_files(),
            ".releaserc.mjs": ManagedFile(__package__, "releaserc.mjs"),
            ".github/workflows/semantic-pull-request.yml": ManagedFile(
                __package__, "semantic-pull-request.yml"
            ),
            ".github/workflows/ci.yml": ManagedFile(__package__, "ci.yml"),
            ".github/workflows/cd.yml": ManagedFile(__package__, "cd.yml"),
        }
