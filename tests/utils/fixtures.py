import os
import shutil
import textwrap
from pathlib import Path

import pytest

from bake.ui import run, run_uv
from bake.utils.constants import CMD_BAKEFILE, CMD_INIT, DEFAULT_FILE_NAME

# Module-level so a test reloading bake.utils.settings cannot detach it from the object src reads
from bake.utils.settings import bake_settings
from tests.utils.cli import RunCli
from tests.utils.script_env import remove_script_envs_under

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
    tmp_path: Path,
    run_cli: RunCli,
    isolated_uv_cache: Path | None,
) -> Path:
    _ = isolated_uv_cache
    return _create_bakefile(tmp_path, run_cli)


@pytest.fixture
def empty_project_folder(tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path | None) -> Path:
    _ = isolated_uv_cache
    tmp_path = _create_bakefile(tmp_path, run_cli, extra_args=["--inline"])
    run(["bakefile", "add", f"bakefile @ {Path.cwd().as_posix()}"], cwd=tmp_path)
    return tmp_path


@pytest.fixture
def uv_project_folder_without_dep(
    tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path | None, isolate_virtual_env: None
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


@pytest.fixture(autouse=True)
def remove_test_script_envs(request: pytest.FixtureRequest):
    # uv names script envs by script path, so each fresh tmp_path leaks one that is never reused
    if "tmp_path" not in request.fixturenames:
        yield
        return
    tmp_path: Path = request.getfixturevalue("tmp_path")
    yield
    remove_script_envs_under(tmp_path)


@pytest.fixture(scope="session")
def isolated_uv_cache(tmp_path_factory: pytest.TempPathFactory):
    """Isolate uv cache on CI to avoid conflicts from restored cache."""
    from bake.utils.settings import bake_settings

    if not bake_settings.github_actions:
        yield None
        return

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
def complex_vars_project(tmp_path: Path, isolated_uv_cache: Path | None) -> Path:
    _ = isolated_uv_cache
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    shutil.copy(COMPLEX_VARS_BAKEBOOK_PATH, bakefile_path)
    return tmp_path


@pytest.fixture
def ctx_test_project(tmp_path: Path, isolated_uv_cache: Path | None) -> Path:
    _ = isolated_uv_cache
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    shutil.copy(CTX_TEST_BAKEBOOK_PATH, bakefile_path)
    return tmp_path


@pytest.fixture(scope="session", autouse=True)
def hide_dotenv_file():
    """Hide .env file during tests to prevent interference."""
    env_file = Path(".env").resolve()
    cache_dir = Path(".cache").resolve()
    cached_env = (cache_dir / ".env").resolve()

    was_moved = False
    if env_file.exists():
        cache_dir.mkdir(exist_ok=True)
        shutil.move(str(env_file), str(cached_env))
        was_moved = True

    try:
        yield
    finally:
        if was_moved and cached_env.exists():
            shutil.move(str(cached_env), str(env_file))


@pytest.fixture(autouse=True, scope="function")
def reset_cwd():
    original = Path.cwd()
    yield
    os.chdir(original)


@pytest.fixture(autouse=True, scope="session")
def no_stray_parent_bakefile(tmp_path_factory: pytest.TempPathFactory) -> None:
    base = tmp_path_factory.getbasetemp().resolve()
    stray = [p / DEFAULT_FILE_NAME for p in base.parents if (p / DEFAULT_FILE_NAME).is_file()]
    if stray:
        pytest.exit(
            f"Walk-up from test temp folders would find {stray[0]}. "
            "Remove it or set --basetemp outside that tree.",
            returncode=1,
        )


@pytest.fixture(autouse=True, scope="function")
def isolate_global_config_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    config_dir = tmp_path_factory.mktemp("global-config")
    monkeypatch.setenv("BAKE_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setattr(bake_settings, "bake_config_dir", config_dir)
    monkeypatch.setattr(bake_settings, "xdg_config_home", config_dir)
    return config_dir


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
