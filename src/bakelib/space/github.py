from pathlib import Path

from bakelib.managed_content import ManagedFile
from bakelib.space import BaseSpace
from bakelib.utils import GitHubActionsEnvVars

ACTIONS_UP_MIN_AGE_DAYS = 3


class GitHubActionsTools(GitHubActionsEnvVars, BaseSpace):
    def _get_mise_tools(self) -> set[str]:
        return super()._get_mise_tools() | {"actionlint", "npm:actions-up", "shellcheck"}

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["actionlint"] = None
        tools["actions-up"] = None
        # actionlint silently skips run: scripts without shellcheck, unlike CI runners
        tools["shellcheck"] = None
        return tools

    def _lint_fast(self) -> None:
        super()._lint_fast()
        self.ctx.run("actionlint")

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
