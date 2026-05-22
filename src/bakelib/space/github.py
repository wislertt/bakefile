from pathlib import Path

from bakelib.space import BaseSpace
from bakelib.utils import GitHubActionsEnvVars


class GitHubActionsTools(GitHubActionsEnvVars, BaseSpace):
    def _get_mise_tools(self) -> set[str]:
        return super()._get_mise_tools() | {"actionlint", "npm:actions-up"}

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["actionlint"] = None
        tools["actions-up"] = None
        return tools

    def lint(self) -> None:
        super().lint()
        self.ctx.run("actionlint")

    def _actions_up(self):
        # Separate method for overriding - subclasses can customize the command
        self.ctx.run("actions-up --yes --min-age 7")

    def _update_project(self) -> None:
        super()._update_project()
        self._actions_up()
