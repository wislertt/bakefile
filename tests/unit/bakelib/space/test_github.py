import pytest

from bake import Context
from bakelib.space.base import BaseSpace
from bakelib.space.github import GitHubActionsTools


def test_github_actions_tools_is_base_space() -> None:
    assert issubclass(GitHubActionsTools, BaseSpace)


class TestGitHubActionsTools:
    def test_get_mise_tools_includes_github_tools(self) -> None:
        github_actions_tools = GitHubActionsTools()
        tools = github_actions_tools._get_mise_tools()
        assert "actionlint" in tools
        assert "npm:actions-up" in tools

    def test_get_required_cli_tools_includes_actionlint_and_actions_up(
        self,
    ) -> None:
        github_actions_tools = GitHubActionsTools()
        tools = github_actions_tools._get_required_cli_tools()
        assert "actionlint" in tools
        assert "actions-up" in tools
        assert tools["actionlint"] is None
        assert tools["actions-up"] is None

    def test_lint_runs_actionlint(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        github_actions_tools = GitHubActionsTools()
        with mock_ctx:
            github_actions_tools.lint()
        captured = capsys.readouterr()
        assert "actionlint" in captured.err

    def test_update_runs_actions_up(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        github_actions_tools = GitHubActionsTools()
        with mock_ctx:
            github_actions_tools.update()
        captured = capsys.readouterr()
        assert "actions-up --yes" in captured.err
