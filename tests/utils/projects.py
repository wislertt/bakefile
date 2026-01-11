import os
import textwrap
from pathlib import Path

import pytest

from bake.ui import run, run_uv
from bake.utils.constants import CMD_BAKEFILE, CMD_INIT, DEFAULT_FILE_NAME
from tests.utils.cli import RunCli


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
def uv_project_folder_without_dep(tmp_path: Path, run_cli: RunCli, isolated_uv_cache: Path) -> Path:
    _ = isolated_uv_cache
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
