import json
import sys
import textwrap
from pathlib import Path

import pytest

from bake.ui import run
from bake.ui.logger import find_log, has_messages_in_logs, parse_pretty_log, strip_ansi
from bake.utils import ENV__BAKE_REINVOKED


def test_reinvocation_actually_switches_python(
    uv_project_folder_with_deps: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reinvoking_msg = "Re-invoking with detected Python:"
    _marker_set_msg = "Re-invocation marker set, skipping Python check"

    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    result = run(["bake", "-vvv", "test-dep"], cwd=uv_project_folder_with_deps, capture_output=True)
    assert result.returncode == 0
    assert "0 -> 1 -> 2" in strip_ansi(result.stdout).strip()

    logs = parse_pretty_log(result.stderr)
    assert has_messages_in_logs(
        logs,
        [_reinvoking_msg, _marker_set_msg],
    )

    reinvoking_msg = find_log(logs, _reinvoking_msg)
    reinvoked_msg = find_log(logs, _marker_set_msg)

    # Verify that the reinvoked process is using the target Python we switched to
    assert reinvoked_msg["sys.executable"] == reinvoking_msg["target_python"]

    result = run(
        ["bakefile", "-vvv"], check=False, cwd=uv_project_folder_with_deps, capture_output=True
    )
    # Exit code 1 because no subcommand provided (shows help)
    assert result.returncode == 1
    logs = parse_pretty_log(result.stderr)
    resolved_bakefile_msg = find_log(logs, "Resolve bakefile path:")
    bakefile_path = Path(resolved_bakefile_msg["bakefile_path"])
    assert "--chdir" in result.stdout and "-C" in result.stdout
    assert bakefile_path.exists()
    assert bakefile_path.is_file()
    assert uv_project_folder_with_deps.as_posix() in bakefile_path.as_posix()


def test_reinvocation_self_heals_corrupted_script_env(
    empty_project_folder: Path,
    isolate_virtual_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A gutted script env (interpreter present, packages gone) must self-heal
    instead of failing forever with ModuleNotFoundError."""
    _ = isolate_virtual_env
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    uv_cache = tmp_path / "uv-cache"
    monkeypatch.setenv("UV_CACHE_DIR", str(uv_cache))

    # sys.executable is the repo venv Python; reinvoke must switch to the script env.
    # (PATH `bake` may be a released install without the code under test.)
    def run_bake():
        return run(
            [sys.executable, "-m", "bake.cli.bake", "-vvv", "--help"],
            cwd=empty_project_folder,
            capture_output=True,
        )

    # First run creates the script env and the frozen lock
    result = run_bake()
    assert result.returncode == 0
    env_dirs = list((uv_cache / "environments-v2").glob("bakefile-*"))
    assert env_dirs, "expected uv script env under isolated cache"
    # POSIX: <env>/lib/python3.X/site-packages; Windows: <env>/Lib/site-packages
    site_packages = next(
        candidate
        for pattern in ("lib/python*/site-packages", "Lib/site-packages")
        for candidate in env_dirs[0].glob(pattern)
    )
    assert (empty_project_folder / "bakefile.py.lock").exists()

    # Gut the env: keep the interpreter, drop every installed package
    site_packages.rename(site_packages.with_name("site-packages.corrupt"))

    # Second run must warn, re-sync (frozen lock), and succeed
    result = run_bake()
    assert result.returncode == 0
    err = strip_ansi(result.stderr)
    assert "is broken" in err
    assert "Re-syncing" in err
    logs = parse_pretty_log(result.stderr)
    assert has_messages_in_logs(logs, ["Syncing bakefile with frozen lock"])

    # Third run is steady state: healthy env, no warning
    result = run_bake()
    assert result.returncode == 0
    assert "is broken" not in strip_ansi(result.stderr)


def test_reinvocation_keeps_invocation_dir_from_subfolder(
    empty_project_folder: Path,
    isolate_virtual_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = isolate_virtual_env
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    bakefile_path = empty_project_folder / "bakefile.py"
    bakefile_path.write_text(
        bakefile_path.read_text()
        + textwrap.dedent("""

            from pathlib import Path

            from bake import Context


            @bakebook.command()
            def identity(ctx: Context) -> None:
                print(f"cwd={Path.cwd()}")
                print(f"invocation_dir={ctx.invocation_dir}")
        """)
    )
    nested = empty_project_folder / "a" / "b"
    nested.mkdir(parents=True)

    result = run(
        [sys.executable, "-m", "bake.cli.bake", "-vvv", "identity"],
        cwd=nested,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    logs = parse_pretty_log(result.stderr)
    assert has_messages_in_logs(logs, ["Re-invoking with detected Python:"])
    out = strip_ansi(result.stdout)
    assert f"cwd={empty_project_folder.resolve()}" in out
    assert f"invocation_dir={nested.resolve()}" in out


def test_reinvocation_runs_global_bakefile_from_unrelated_dir(
    empty_project_folder: Path,
    isolate_virtual_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    _ = isolate_virtual_env
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    monkeypatch.setenv("BAKE_CONFIG_DIR", str(empty_project_folder))
    bakefile_path = empty_project_folder / "bakefile.py"
    bakefile_path.write_text(
        bakefile_path.read_text()
        + textwrap.dedent("""

            from pathlib import Path

            from bake import Context


            @bakebook.command()
            def identity(ctx: Context) -> None:
                print(f"file={__file__}")
                print(f"cwd={Path.cwd()}")
                print(f"invocation_dir={ctx.invocation_dir}")
        """)
    )
    unrelated = tmp_path_factory.mktemp("unrelated")

    result = run(
        [sys.executable, "-m", "bake.cli.bake", "-vvv", "-g", "identity"],
        cwd=unrelated,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    logs = parse_pretty_log(result.stderr)
    assert has_messages_in_logs(logs, ["Re-invoking with detected Python:"])
    out = strip_ansi(result.stdout)
    assert f"file={bakefile_path.resolve()}" in out
    assert f"cwd={empty_project_folder.resolve()}" in out
    assert f"invocation_dir={unrelated.resolve()}" in out


@pytest.mark.parametrize("use_global", [True, False], ids=["global", "subfolder"])
def test_reinvocation_ignores_cwd_package_shadowing_bakefile_namespace_import(
    empty_project_folder: Path,
    isolate_virtual_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    use_global: bool,
) -> None:
    _ = isolate_virtual_env
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    bakefile_path = empty_project_folder / "bakefile.py"
    # Namespace package (no __init__.py) beside the bakefile
    namespace_dir = empty_project_folder / "src" / "python"
    namespace_dir.mkdir(parents=True)
    (namespace_dir / "x.py").write_text(
        textwrap.dedent("""
            import json
            import sys

            from bake import Bakebook, Context

            bakebook = Bakebook()


            @bakebook.command()
            def identity(ctx: Context) -> None:
                print(f"invocation_dir={ctx.invocation_dir}")
                print(f"sys_path={json.dumps(sys.path)}")
        """)
    )
    header, _ = bakefile_path.read_text().split("# ///\n", 1)
    bakefile_path.write_text(header + "# ///\n\nfrom src.python.x import bakebook\n")

    if use_global:
        monkeypatch.setenv("BAKE_CONFIG_DIR", str(empty_project_folder))
        cwd = tmp_path_factory.mktemp("unrelated")
        args = ["-g", "identity"]
    else:
        cwd = empty_project_folder / "sub"
        args = ["identity"]
    # Regular package in cwd that would shadow the bakefile's namespace `src`
    (cwd / "src").mkdir(parents=True)
    (cwd / "src" / "__init__.py").write_text("")

    result = run(
        [sys.executable, "-m", "bake.cli.bake", "-vvv", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    logs = parse_pretty_log(result.stderr)
    assert has_messages_in_logs(logs, ["Re-invoking with detected Python:"])
    out = strip_ansi(result.stdout)
    assert f"invocation_dir={cwd.resolve()}" in out
    sys_path_line = next(line for line in out.splitlines() if line.startswith("sys_path="))
    sys_path = json.loads(sys_path_line.removeprefix("sys_path="))
    # "" means the process cwd, which is the bakefile dir by the time the command runs
    assert "" not in sys_path
    assert cwd.resolve() not in [Path(entry).resolve() for entry in sys_path]
