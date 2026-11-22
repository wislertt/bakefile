import os
import textwrap
from pathlib import Path

import pytest

from bake.utils.constants import CMD_BAKE, CMD_BAKEFILE
from bake.utils.settings import BakeSettings, bake_settings
from tests.utils.cli import RunCli


def _write_identity_bakefile(path: Path, name: str, inline: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = '# /// script\n# dependencies = ["bakefile"]\n# ///\n' if inline else ""
    path.write_text(
        header
        + textwrap.dedent(f"""
            from pathlib import Path

            from bake import Bakebook, Context, command


            class Identity(Bakebook):
                @command()
                def identity(self, ctx: Context) -> None:
                    print("book={name}")
                    print(f"cwd={{Path.cwd()}}")
                    print(f"invocation_dir={{ctx.invocation_dir}}")


            bakebook = Identity()
        """)
    )


def _parse(out: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path.resolve()
    _write_identity_bakefile(root / "project" / "bakefile.py", "project")
    _write_identity_bakefile(root / "project" / "tools.py", "project-tools")
    (root / "project" / "a" / "b").mkdir(parents=True)
    return root


class TestWalkUp:
    def test_runs_nearest_parent_bakefile_in_its_directory(
        self, tree: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["book"] == "project"
        assert identity["cwd"] == str(tree / "project")

    def test_nearest_bakefile_wins(self, tree: Path, run_cli: RunCli) -> None:
        _write_identity_bakefile(tree / "project" / "a" / "bakefile.py", "nested")
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["book"] == "nested"
        assert identity["cwd"] == str(tree / "project" / "a")

    def test_file_name_option_walks_up(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-f", "tools.py", "identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "project-tools"

    def test_invocation_dir_is_where_bake_was_called(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["invocation_dir"] == str(tree / "project" / "a" / "b")
        assert identity["cwd"] == str(tree / "project")

    def test_chained_commands_run_against_one_file(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-c", "identity", "identity"])

        assert captured.exit_code == 0, captured.err
        books = [line for line in captured.out.splitlines() if line.startswith("book=")]
        cwds = [line for line in captured.out.splitlines() if line.startswith("cwd=")]
        assert books == ["book=project", "book=project"]
        assert cwds == [f"cwd={tree / 'project'}"] * 2

    def test_help_shows_loaded_bakefile_path(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["--help"], columns=500)

        assert captured.exit_code == 0, captured.err
        assert f"Using: {tree / 'project' / 'bakefile.py'}" in captured.out
        assert "identity" in captured.out


class TestExactDirectory:
    def test_chdir_option_uses_only_that_directory(self, tree: Path, run_cli: RunCli) -> None:
        _write_identity_bakefile(tree / "project" / "a" / "bakefile.py", "nested")
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=tree / "project" / "a", args=["identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["book"] == "nested"
        assert identity["invocation_dir"] == str(tree)

    def test_chdir_option_does_not_walk_up(self, tree: Path, run_cli: RunCli) -> None:
        captured = run_cli(
            command=CMD_BAKE, dir_path=tree / "project" / "a" / "b", args=["identity"]
        )

        assert captured.exit_code == 1
        assert "book=" not in captured.out
        assert f"Searched in: {tree / 'project' / 'a' / 'b'}\n" in captured.err
        assert "parent directories" not in captured.err


class TestBakefileCli:
    def test_subcommand_resolves_by_walk_up(self, tree: Path, run_cli: RunCli) -> None:
        _write_identity_bakefile(tree / "project" / "bakefile.py", "project", inline=True)
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-n", "lock"])

        assert captured.exit_code == 0, captured.err
        assert "uv lock --script bakefile.py" in captured.err

    @pytest.mark.parametrize(
        ("args", "inline", "exit_code"),
        [
            (["-n", "lock"], True, 0),
            (["-n", "lock"], False, 1),
            (["add-inline"], True, 0),
        ],
    )
    def test_subcommand_names_resolved_bakefile_on_stderr(
        self,
        tree: Path,
        run_cli: RunCli,
        monkeypatch: pytest.MonkeyPatch,
        args: list[str],
        inline: bool,
        exit_code: int,
    ) -> None:
        _write_identity_bakefile(tree / "project" / "bakefile.py", "project", inline=inline)
        monkeypatch.setattr(bake_settings, "bake_reinvoked", False)
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=args)

        assert captured.exit_code == exit_code, captured.err
        assert f"Using: {tree / 'project' / 'bakefile.py'}" in captured.err
        assert "Using:" not in captured.out

    def test_reinvoked_child_does_not_name_bakefile_again(
        self, tree: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_identity_bakefile(tree / "project" / "bakefile.py", "project", inline=True)
        monkeypatch.setattr(bake_settings, "bake_reinvoked", True)
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-n", "lock"])

        assert captured.exit_code == 0, captured.err
        assert "Using:" not in captured.err

    def test_subcommand_help_does_not_name_bakefile(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project" / "a" / "b")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["lock", "--help"])

        assert captured.exit_code == 0, captured.err
        assert "Using:" not in captured.out + captured.err

    def test_init_does_not_name_bakefile(self, tree: Path, run_cli: RunCli) -> None:
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["init"])

        assert captured.exit_code != 0
        assert "Using:" not in captured.err

    def test_subcommand_without_bakefile_does_not_name_one(
        self, tmp_path: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(bake_settings, "bake_reinvoked", False)
        os.chdir(tmp_path)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-n", "lock"])

        assert captured.exit_code != 0
        assert "Using:" not in captured.err

    def test_init_creates_in_current_directory_despite_parent_bakefile(
        self, tree: Path, run_cli: RunCli
    ) -> None:
        nested = tree / "project" / "a" / "b"
        os.chdir(nested)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["init"])

        assert captured.exit_code == 0, captured.err
        assert (nested / "bakefile.py").is_file()
        assert "Using:" not in captured.err
        assert "book=project" in (tree / "project" / "bakefile.py").read_text()

    def test_init_with_relative_chdir_option_creates_there(
        self, tree: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=Path("a") / "b", args=["init"])

        assert captured.exit_code == 0, captured.err
        assert (tree / "project" / "a" / "b" / "bakefile.py").is_file()

    def test_run_script_path_is_relative_to_invocation_dir(
        self, empty_project_folder: Path, run_cli: RunCli
    ) -> None:
        nested = empty_project_folder / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "nested_script.py").write_text("print('hello from nested script')")
        os.chdir(nested)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["run", "nested_script.py"])

        assert captured.exit_code == 0, captured.err
        assert "hello from nested script" in captured.out


@pytest.fixture
def global_dir(tree: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tree / "global"
    _write_identity_bakefile(directory / "bakefile.py", "global")
    _write_identity_bakefile(directory / "tools.py", "global-tools")
    monkeypatch.setattr(bake_settings, "bake_config_dir", directory)
    return directory


class TestGlobal:
    def test_global_option_uses_global_bakefile_inside_project(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree / "project" / "a")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-g", "identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["book"] == "global"
        assert identity["cwd"] == str(global_dir)
        assert identity["invocation_dir"] == str(tree / "project" / "a")

    def test_global_option_with_file_name_uses_global_file(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        _ = global_dir
        os.chdir(tree / "project")

        captured = run_cli(
            command=CMD_BAKE, dir_path=None, args=["-g", "-f", "tools.py", "identity"]
        )

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "global-tools"

    def test_global_option_with_chdir_is_usage_error(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        _ = global_dir

        captured = run_cli(command=CMD_BAKE, dir_path=tree / "project", args=["-g", "identity"])

        assert captured.exit_code == 2
        assert "book=" not in captured.out
        assert "cannot be used with" in captured.err

    def test_global_option_without_global_file_suggests_init(
        self, tree: Path, run_cli: RunCli, isolate_global_config_dir: Path
    ) -> None:
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-g", "identity"])

        assert captured.exit_code == 1
        assert "book=" not in captured.out
        assert str(isolate_global_config_dir.resolve() / "bakefile.py") in captured.err
        assert "bakefile -g init" in captured.err

    def test_symlinked_global_dir_runs_in_resolved_dir(
        self, tree: Path, global_dir: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        link = tree / "link"
        link.symlink_to(global_dir, target_is_directory=True)
        monkeypatch.setattr(bake_settings, "bake_config_dir", link)
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-g", "identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["cwd"] == str(global_dir)

    def test_help_marks_global_bakefile(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-g", "--help"], columns=500)

        assert captured.exit_code == 0, captured.err
        assert f"Using: {global_dir / 'bakefile.py'} (global)" in captured.out

    def test_help_does_not_mark_project_bakefile(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        _ = global_dir
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["--help"], columns=500)

        assert captured.exit_code == 0, captured.err
        assert "(global)" not in captured.out


class TestGlobalFallback:
    def test_falls_back_to_global_when_walk_up_finds_nothing(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        elsewhere = tree / "elsewhere"
        elsewhere.mkdir()
        os.chdir(elsewhere)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        identity = _parse(captured.out)
        assert identity["book"] == "global"
        assert identity["cwd"] == str(global_dir)
        assert identity["invocation_dir"] == str(elsewhere)
        assert "global" not in captured.err.lower()

    def test_file_name_falls_back_to_global_file_of_same_name(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        _ = global_dir
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["-f", "tools.py", "identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "global-tools"

    def test_help_marks_fallback_as_global(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["--help"], columns=500)

        assert captured.exit_code == 0, captured.err
        assert f"Using: {global_dir / 'bakefile.py'} (global)" in captured.out

    def test_chdir_option_never_falls_back(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        empty = tree / "empty"
        empty.mkdir()

        captured = run_cli(command=CMD_BAKE, dir_path=empty, args=["identity"])

        assert captured.exit_code == 1
        assert "book=" not in captured.out
        assert f"Global: {global_dir / 'bakefile.py'} (exists)" in captured.err

    def test_missing_command_is_not_looked_up_in_global(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        (global_dir / "bakefile.py").write_text(
            (global_dir / "bakefile.py").read_text()
            + "\n\n@bakebook.command()\ndef only_global() -> None:\n    print('ran global')\n"
        )
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["only-global"])

        assert captured.exit_code != 0
        assert "ran global" not in captured.out

    def test_without_global_file_not_found_names_search_and_global(
        self, tree: Path, run_cli: RunCli, isolate_global_config_dir: Path
    ) -> None:
        elsewhere = tree / "elsewhere"
        elsewhere.mkdir()
        os.chdir(elsewhere)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 1
        assert f"Searched in: {elsewhere} and parent directories" in captured.err
        global_path = isolate_global_config_dir.resolve() / "bakefile.py"
        assert f"Global: {global_path} (not found)" in captured.err

    def test_without_global_file_bare_bake_warns_with_global_line(
        self, tmp_path: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tmp_path)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=[])

        assert "and parent directories" in captured.out
        assert "Global: " in captured.out

    def test_xdg_config_home_used_when_bake_config_dir_unset(
        self, tree: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_identity_bakefile(tree / "xdg" / "bake" / "bakefile.py", "xdg")
        monkeypatch.delenv("BAKE_CONFIG_DIR")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tree / "xdg"))
        fresh_settings = BakeSettings()
        monkeypatch.setattr(bake_settings, "bake_config_dir", fresh_settings.bake_config_dir)
        monkeypatch.setattr(bake_settings, "xdg_config_home", fresh_settings.xdg_config_home)
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "xdg"

    def test_home_config_used_when_bake_config_dir_and_xdg_unset(
        self, tree: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_identity_bakefile(tree / "home" / ".config" / "bake" / "bakefile.py", "home")
        monkeypatch.setenv("HOME", str(tree / "home"))
        monkeypatch.setenv("USERPROFILE", str(tree / "home"))
        monkeypatch.setattr(bake_settings, "bake_config_dir", None)
        monkeypatch.setattr(bake_settings, "xdg_config_home", None)
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "home"

    def test_relative_xdg_config_home_is_ignored(
        self, tree: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_identity_bakefile(tree / "home" / ".config" / "bake" / "bakefile.py", "home")
        _write_identity_bakefile(tree / "xdg" / "bake" / "bakefile.py", "xdg")
        monkeypatch.setenv("HOME", str(tree / "home"))
        monkeypatch.setenv("USERPROFILE", str(tree / "home"))
        monkeypatch.setattr(bake_settings, "bake_config_dir", None)
        monkeypatch.setattr(bake_settings, "xdg_config_home", Path("xdg"))
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKE, dir_path=None, args=["identity"])

        assert captured.exit_code == 0, captured.err
        assert _parse(captured.out)["book"] == "home"


class TestBakefileCliGlobal:
    def test_global_lock_acts_on_global_bakefile(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        _write_identity_bakefile(global_dir / "bakefile.py", "global", inline=True)
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-g", "-n", "lock"])

        assert captured.exit_code == 0, captured.err
        assert "uv lock --script bakefile.py" in captured.err

    def test_global_lock_without_global_file_suggests_init(
        self, tree: Path, run_cli: RunCli, isolate_global_config_dir: Path
    ) -> None:
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-g", "-n", "lock"])

        assert captured.exit_code == 1
        assert str(isolate_global_config_dir.resolve() / "bakefile.py") in captured.err
        assert "bakefile -g init" in captured.err

    def test_lock_falls_back_to_global_bakefile(
        self, tree: Path, global_dir: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_identity_bakefile(global_dir / "bakefile.py", "global", inline=True)
        monkeypatch.setattr(bake_settings, "bake_reinvoked", False)
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-n", "lock"])

        assert captured.exit_code == 0, captured.err
        assert f"Using: {global_dir / 'bakefile.py'}" in captured.err

    def test_global_init_creates_global_dir_and_bakefile(
        self, tree: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        global_dir = tree / "new" / "bake"
        monkeypatch.setattr(bake_settings, "bake_config_dir", global_dir)
        os.chdir(tree / "project")

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-g", "init"])

        assert captured.exit_code == 0, captured.err
        assert (global_dir / "bakefile.py").is_file()
        assert "book=project" in (tree / "project" / "bakefile.py").read_text()

    def test_global_init_refuses_to_overwrite(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        os.chdir(tree)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["-g", "init"])

        assert captured.exit_code == 1
        assert "book=global" in (global_dir / "bakefile.py").read_text()

    def test_plain_init_ignores_global_fallback(
        self, tree: Path, global_dir: Path, run_cli: RunCli
    ) -> None:
        elsewhere = tree / "elsewhere"
        elsewhere.mkdir()
        os.chdir(elsewhere)

        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["init"])

        assert captured.exit_code == 0, captured.err
        assert (elsewhere / "bakefile.py").is_file()
        assert "book=global" in (global_dir / "bakefile.py").read_text()
