import os
import shutil
import textwrap
from pathlib import Path

import pytest

from bake.ui import run, run_uv
from bake.utils.constants import CMD_BAKEFILE, CMD_INIT, DEFAULT_FILE_NAME
from tests.utils.cli import RunCli

# Path to the complex vars bakebook file
COMPLEX_VARS_BAKEBOOK_PATH = Path(__file__).parent / "bakefiles" / "complex_vars.py"
# Path to the ctx test bakebook file
CTX_TEST_BAKEBOOK_PATH = Path(__file__).parent / "bakefiles" / "ctx_test.py"


def _create_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
    extra_args: list[str] | None = None,
) -> Path:
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    assert not bakefile_path.exists()

    args = [CMD_INIT, *(extra_args or [])]
    run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=args)

    assert bakefile_path.exists()
    return tmp_path


@pytest.fixture
def empty_project_folder_no_inline(
    tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path
) -> Path:
    _ = isolated_uv_cache
    return _create_bakefile(tmp_path, run_cli)


@pytest.fixture
def empty_project_folder(tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path) -> Path:
    _ = isolated_uv_cache
    tmp_path = _create_bakefile(tmp_path, run_cli, extra_args=["--inline"])
    run(["bakefile", "add", f"bakefile @ {Path.cwd().as_posix()}"], cwd=tmp_path)
    return tmp_path


@pytest.fixture
def uv_project_folder_without_dep(
    tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path, isolate_virtual_env: None
) -> Path:
    _ = isolated_uv_cache
    _ = isolate_virtual_env
    run_uv(["init"], cwd=tmp_path)
    return _create_bakefile(tmp_path, run_cli)


@pytest.fixture
def uv_project_folder(uv_project_folder_without_dep: Path) -> Path:
    run_uv(["add", f"bakefile @ {Path.cwd().as_posix()}"], cwd=uv_project_folder_without_dep)
    return uv_project_folder_without_dep


@pytest.fixture
def uv_project_folder_with_deps(
    uv_project_folder_without_dep: Path, isolate_virtual_env: None
) -> Path:
    _ = isolate_virtual_env
    run_uv(["add", f"bakefile @ {Path.cwd().as_posix()}"], cwd=uv_project_folder_without_dep)
    run_uv(["add", "leetcode-py-sdk"], cwd=uv_project_folder_without_dep)

    bakefile_path = uv_project_folder_without_dep / DEFAULT_FILE_NAME
    bakefile_content = textwrap.dedent("""
        from leetcode_py import ListNode

        @bakebook.command()
        def test_dep():
            from leetcode_py import ListNode

            x = ListNode.from_list(list(range(3)))
            console.echo(x)
    """)
    bakefile_path.write_text(bakefile_path.read_text() + bakefile_content)
    return uv_project_folder_without_dep


@pytest.fixture(scope="session")
def isolated_uv_cache(tmp_path_factory: pytest.TempPathFactory):
    """Isolate uv cache for the entire test session to avoid cache conflicts."""
    temp_session_dir = tmp_path_factory.mktemp("uv-cache-session")
    uv_cache = temp_session_dir / ".cache" / "uv"
    uv_cache.mkdir(parents=True, exist_ok=True)

    old_value = os.environ.get("UV_CACHE_DIR")
    os.environ["UV_CACHE_DIR"] = str(uv_cache)

    yield uv_cache

    # Cleanup - restore original value
    if old_value is None:
        os.environ.pop("UV_CACHE_DIR", None)
    else:
        os.environ["UV_CACHE_DIR"] = old_value


@pytest.fixture
def no_bakebook_dir(tmp_path: Path) -> Path:
    (tmp_path / "bakefile.py").write_text("")
    return tmp_path


@pytest.fixture
def no_bakefile_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def complex_vars_project(tmp_path: Path, isolated_uv_cache: Path) -> Path:
    _ = isolated_uv_cache
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    shutil.copy(COMPLEX_VARS_BAKEBOOK_PATH, bakefile_path)
    return tmp_path


@pytest.fixture
def ctx_test_project(tmp_path: Path, isolated_uv_cache: Path) -> Path:
    _ = isolated_uv_cache
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    shutil.copy(CTX_TEST_BAKEBOOK_PATH, bakefile_path)
    return tmp_path


@pytest.fixture(autouse=True, scope="function")
def disable_colors():
    from bake.utils import ENV_NO_COLOR

    os.environ[ENV_NO_COLOR] = "1"


def get_project_env(project_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    venv_bin = str(project_dir / ".venv" / "bin")
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    env["VIRTUAL_ENV"] = str(project_dir / ".venv")
    return env


@pytest.fixture
def isolate_virtual_env(monkeypatch: pytest.MonkeyPatch):
    old_virtual_env = os.environ.get("VIRTUAL_ENV")
    if "VIRTUAL_ENV" in os.environ:
        monkeypatch.delenv("VIRTUAL_ENV")
    yield
    if old_virtual_env is not None:
        monkeypatch.setenv("VIRTUAL_ENV", old_virtual_env)


@pytest.fixture(autouse=True, scope="session")
def prevent_reinvocation():
    from bake.utils.settings import bake_settings

    old_value = bake_settings.bake_reinvoked
    bake_settings.bake_reinvoked = True
    yield
    bake_settings.bake_reinvoked = old_value
