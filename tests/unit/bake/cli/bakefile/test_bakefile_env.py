from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from bake.cli.bakefile.env import EnvInput, _build_env_dict, _env, _lookup_field
from bake.utils.constants import CMD_BAKEFILE
from tests.conftest import RunCli
from tests.utils.bakefiles.complex_vars import ComplexVarsBakebook


class TestEnvSingleValue:
    @pytest.mark.parametrize(
        "field_name,expected",
        [
            ("name", "app"),
            ("count", "42"),
            ("enabled", "true"),
            ("nullable", ""),
            ("tags", '\'["a","b"]\''),
            ("config", '\'{"key":"value"}\''),
            ("NAME", "app"),
            ("Name", "app"),
        ],
    )
    def test_env_field_value(
        self, complex_vars_project: Path, run_cli: RunCli, field_name: str, expected: str
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", field_name],
        ).stripped()

        assert result.exit_code == 0
        assert result.out.strip() == expected


class TestEnvErrors:
    @pytest.mark.parametrize(
        "args,expected_exit_code,expected_err_pattern",
        [
            (["env", "INVALID_VAR"], 2, "INVALID_VAR"),
            (["env", "NAME", "COUNT"], 2, "Only one variable"),
            (["env", "--", "nonexistent_command_xyz"], 127, "Command not found"),
            (["env", "NAME", "-d"], 2, "No such option"),
        ],
    )
    def test_env_error(
        self,
        complex_vars_project: Path,
        run_cli: RunCli,
        args: list[str],
        expected_exit_code: int,
        expected_err_pattern: str,
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=args,
        ).stripped()

        assert result.exit_code == expected_exit_code
        assert expected_err_pattern in result.err

    def test_env_no_args_shows_help(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env"],
        ).stripped()

        assert result.exit_code == 1
        assert "Usage" in result.out or "usage" in result.out


class TestEnvWrapMode:
    def test_env_wrap_exit_code(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "--", "echo", "hello"],
        ).stripped()

        assert result.exit_code == 0

    def test_env_wrap_injects_env(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        output_file = complex_vars_project / "env_test_output.txt"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "--", "sh", "-c", f"echo $NAME > {output_file}"],
        ).stripped()

        assert result.exit_code == 0
        assert output_file.read_text().strip() == "app"

    def test_env_wrap_captures_subprocess_output(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "--", "sh", "-c", "echo hello"],
        ).stripped()

        assert result.exit_code == 0
        assert "hello" in result.out

    def test_env_wrap_injects_single_var(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "NAME", "--", "sh", "-c", "echo $NAME"],
        ).stripped()

        assert result.exit_code == 0
        assert result.out.strip() == "app"

    def test_env_wrap_injects_selective_vars(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "NAME", "COUNT", "--", "sh", "-c", "echo $NAME $COUNT"],
        ).stripped()

        assert result.exit_code == 0
        assert result.out.strip() == "app 42"

    def test_env_wrap_selective_does_not_inject_unspecified(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "NAME", "--", "sh", "-c", "echo $NAME $COUNT"],
        ).stripped()

        assert result.exit_code == 0
        assert result.out.strip() == "app"  # NAME injected, COUNT is empty (not injected)

    def test_env_wrap_preserves_existing_env(
        self, complex_vars_project: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MY_EXISTING_VAR", "from_parent_shell")

        output_file = complex_vars_project / "env_test_output.txt"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "--", "sh", "-c", f"echo $MY_EXISTING_VAR > {output_file}"],
        ).stripped()

        assert result.exit_code == 0
        assert output_file.read_text().strip() == "from_parent_shell"


class TestBuildEnvDict:
    def test_keys_are_uppercase(self) -> None:
        bakebook = ComplexVarsBakebook()
        env_dict = _build_env_dict(bakebook)

        assert "NAME" in env_dict
        assert "COUNT" in env_dict
        assert "ENABLED" in env_dict

    def test_values_formatted(self) -> None:
        bakebook = ComplexVarsBakebook()
        env_dict = _build_env_dict(bakebook)

        assert env_dict["NAME"] == "app"
        assert env_dict["COUNT"] == "42"
        assert env_dict["ENABLED"] == "true"
        assert env_dict["NULLABLE"] == ""
        assert "**********" in env_dict["API_KEY"]


class TestLookupField:
    def test_exact_match(self) -> None:
        data = {"name": "app", "count": 42}
        assert _lookup_field(data, "name") == "app"

    def test_case_insensitive(self) -> None:
        data = {"name": "app", "count": 42}
        assert _lookup_field(data, "NAME") == "app"
        assert _lookup_field(data, "Name") == "app"

    def test_not_found(self) -> None:
        import typer

        data = {"name": "app", "count": 42}
        with pytest.raises(typer.BadParameter, match="not found"):
            _lookup_field(data, "missing")


class TestEnvRuntimeError:
    def test_env_raises_runtime_error_when_bakebook_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["bakefile", "env", "NAME"])

        mock_ctx = MagicMock()
        mock_ctx.obj.bakebook = None
        mock_ctx.obj.get_bakebook = MagicMock()

        from bake.cli.bakefile.env import env as env_cmd

        with pytest.raises(RuntimeError, match="Bakebook not found"):
            env_cmd(mock_ctx, var_names="NAME")


class TestEnvNoCommandAfterDash:
    def test_env_double_dash_no_command(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "--"],
        ).stripped()

        assert result.exit_code == 2
        assert "No command specified after --" in result.err


class TestEnvInternal:
    def test_env_handles_empty_var_names_without_double_dash(self) -> None:
        bakebook = ComplexVarsBakebook()
        env_input = EnvInput(var_names=[], cmd=None, reveal_secrets=False)
        with pytest.raises(typer.Exit) as exc_info:
            _env(bakebook=bakebook, env_input=env_input)
        assert exc_info.value.exit_code == 0

    def test_env_wrap_handles_no_env_in_argv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bakebook = ComplexVarsBakebook()
        monkeypatch.setattr("sys.argv", ["bakefile", "--", "echo", "hello"])

        with (
            patch("bake.cli.bakefile.env._build_env_dict", return_value={"KEY": "val"}),
            patch("bake.cli.bakefile.env._run", return_value=MagicMock(returncode=0)),
        ):
            env_input = EnvInput(var_names=[], cmd=["echo", "hello"], reveal_secrets=False)
            with pytest.raises(typer.Exit) as exc_info:
                _env(bakebook=bakebook, env_input=env_input)
            assert exc_info.value.exit_code == 0


class TestEnvSecret:
    def test_env_secret_field_masked_by_default(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "api_key"],
        ).stripped()

        assert result.exit_code == 0
        assert "super_secret_key_123" not in result.out
        assert "**********" in result.out

    def test_env_secret_field_revealed_with_flag(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "api_key", "-s"],
        ).stripped()

        assert result.exit_code == 0
        assert "super_secret_key_123" in result.out

    def test_env_secret_wrap_revealed(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "api_key", "-s", "--", "sh", "-c", "echo $API_KEY"],
        ).stripped()

        assert result.exit_code == 0
        assert "super_secret_key_123" in result.out

    def test_env_secret_wrap_masked_without_flag(
        self, complex_vars_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["env", "api_key", "--", "sh", "-c", "echo $API_KEY"],
        ).stripped()

        assert result.exit_code == 0
        assert "super_secret_key_123" not in result.out

    def test_env_build_env_dict_reveals_secrets(self) -> None:
        bakebook = ComplexVarsBakebook()
        env_dict = _build_env_dict(bakebook, reveal_secrets=True)
        assert env_dict["API_KEY"] == "super_secret_key_123"
        assert env_dict["PASSWORD"] == "my_password"

    def test_env_build_env_dict_masks_secrets_by_default(self) -> None:
        bakebook = ComplexVarsBakebook()
        env_dict = _build_env_dict(bakebook, reveal_secrets=False)
        assert "super_secret_key_123" not in env_dict["API_KEY"]
        assert "my_password" not in env_dict["PASSWORD"]


class TestEnvParseEnvInput:
    def test_unknown_option_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import click

        monkeypatch.setattr("sys.argv", ["bakefile", "env", "NAME", "-d"])

        with pytest.raises(click.NoSuchOption):
            from bake.cli.bakefile.env import _parse_env_input

            _parse_env_input()

    def test_known_option_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["bakefile", "env", "NAME", "-s"])

        from bake.cli.bakefile.env import _parse_env_input

        result = _parse_env_input(reveal_secrets=True)
        assert result.var_names == ["NAME"]
        assert result.reveal_secrets is True

    def test_no_env_in_argv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When 'env' is not in argv, env_idx=-1, so raw_args starts from index 0."""
        monkeypatch.setattr("sys.argv", ["bakefile", "NAME"])

        from bake.cli.bakefile.env import _parse_env_input

        result = _parse_env_input()
        # env_idx=-1, so raw_args = sys.argv[0:] = ["bakefile", "NAME"]
        assert result.var_names == ["bakefile", "NAME"]

    def test_double_dash_no_command_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import click

        monkeypatch.setattr("sys.argv", ["bakefile", "env", "--"])

        from bake.cli.bakefile.env import _parse_env_input

        with pytest.raises(click.UsageError):
            _parse_env_input()

    def test_double_dash_with_vars_and_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["bakefile", "env", "VAR1", "VAR2", "--", "echo", "hi"])

        from bake.cli.bakefile.env import _parse_env_input

        result = _parse_env_input()
        assert result.var_names == ["VAR1", "VAR2"]
        assert result.cmd == ["echo", "hi"]

    def test_double_dash_with_options_mixed_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["bakefile", "env", "VAR1", "-s", "--", "echo", "hi"])

        from bake.cli.bakefile.env import _parse_env_input

        result = _parse_env_input(reveal_secrets=True)
        assert result.var_names == ["VAR1"]
        assert result.cmd == ["echo", "hi"]
        assert result.reveal_secrets is True
