from unittest.mock import MagicMock, patch

import orjson
import pytest

from bake import Context
from bakelib.space.base import BaseSpace, local_mise_tools
from bakelib.space.github import GitHubActionsTools


def test_github_actions_tools_is_base_space() -> None:
    assert issubclass(GitHubActionsTools, BaseSpace)


def _mise_tools_run(tools: list[str], calls: list[tuple[str, dict[str, object]]]):
    def capture_run(cmd: str, **kwargs: object) -> object:
        calls.append((cmd, kwargs))
        result = MagicMock()
        result.stdout = orjson.dumps({tool: {} for tool in tools})
        return result

    return capture_run


class TestGitHubActionsTools:
    def test_get_mise_tools_includes_github_tools(self) -> None:
        github_actions_tools = GitHubActionsTools()
        tools = github_actions_tools._get_mise_tools()
        assert {"jactionlint", "npm:actions-up", "shellcheck"} <= tools
        assert "actionlint" not in tools

    def test_get_required_cli_tools_includes_github_tools(
        self,
    ) -> None:
        github_actions_tools = GitHubActionsTools()
        tools = github_actions_tools._get_required_cli_tools()
        assert tools["jactionlint"] is None
        assert tools["actions-up"] is None
        assert tools["shellcheck"] is None
        assert "actionlint" not in tools

    def test_lint_runs_jactionlint_offline(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        github_actions_tools = GitHubActionsTools()
        with mock_ctx:
            github_actions_tools.lint()
        captured = capsys.readouterr()
        assert "jactionlint --profile default\n" in captured.err
        assert "--online" not in captured.err

    def test_lint_slow_runs_jactionlint_online(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        github_actions_tools = GitHubActionsTools()
        with mock_ctx:
            github_actions_tools.lint(slow=1)
        captured = capsys.readouterr()
        assert "jactionlint --profile default --online" in captured.err

    def test_lint_leaves_profile_to_config_when_unset(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        class ConfigProfileTools(GitHubActionsTools):
            jactionlint_profile = None

        with mock_ctx:
            ConfigProfileTools().lint()
        captured = capsys.readouterr()
        assert "jactionlint\n" in captured.err
        assert "--profile" not in captured.err

    def test_update_runs_actions_up(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        github_actions_tools = GitHubActionsTools()
        with mock_ctx:
            github_actions_tools.update()
        captured = capsys.readouterr()
        assert "actions-up --yes" in captured.err


class TestRemoveActionlintMigration:
    @pytest.fixture(autouse=True)
    def real_local_mise_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("bakelib.space.github.local_mise_tools", local_mise_tools)

    def test_declared_by_github_actions_tools(self) -> None:
        migrations = GitHubActionsTools().collect_migrations()
        assert "remove-actionlint" in migrations

    def test_applies_while_actionlint_is_a_local_mise_tool(self, mock_ctx: Context) -> None:
        migration = GitHubActionsTools().collect_migrations()["remove-actionlint"]
        calls: list[tuple[str, dict[str, object]]] = []
        with (
            mock_ctx,
            patch.object(
                mock_ctx, "run", side_effect=_mise_tools_run(["actionlint", "shellcheck"], calls)
            ),
        ):
            assert migration.check(mock_ctx)

        assert calls == [
            (
                "mise list --local --current --json",
                {
                    "stream": False,
                    "echo": False,
                    "capture_output": True,
                    "clean_capture_output": False,
                    "dry_run": False,
                    "check": False,
                },
            )
        ]

    def test_does_not_apply_without_actionlint(self, mock_ctx: Context) -> None:
        migration = GitHubActionsTools().collect_migrations()["remove-actionlint"]
        calls: list[tuple[str, dict[str, object]]] = []
        with (
            mock_ctx,
            patch.object(
                mock_ctx, "run", side_effect=_mise_tools_run(["jactionlint", "shellcheck"], calls)
            ),
        ):
            assert not migration.check(mock_ctx)

    def test_apply_unuses_actionlint(self, mock_ctx: Context) -> None:
        migration = GitHubActionsTools().collect_migrations()["remove-actionlint"]
        calls: list[tuple[str, dict[str, object]]] = []
        with mock_ctx, patch.object(mock_ctx, "run", side_effect=_mise_tools_run([], calls)):
            migration.apply(mock_ctx)

        assert [cmd for cmd, _ in calls] == ["mise unuse actionlint"]

    def test_setup_dev_removes_actionlint_before_adding_jactionlint(
        self, mock_ctx: Context
    ) -> None:
        calls: list[tuple[str, dict[str, object]]] = []
        with (
            mock_ctx,
            patch.object(
                mock_ctx, "run", side_effect=_mise_tools_run(["actionlint", "shellcheck"], calls)
            ),
            patch.object(GitHubActionsTools, "_setup_platform_tools"),
            patch.object(GitHubActionsTools, "_setup_project"),
            patch("bakelib.space.base.install_mise_tools"),
        ):
            GitHubActionsTools().setup_dev()

        cmds = [cmd for cmd, _ in calls]
        assert cmds.index("mise unuse actionlint") < cmds.index("mise use 'jactionlint'")
