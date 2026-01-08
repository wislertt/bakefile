import os

import pytest

from bake.utils.env import _BAKE_REINVOKED
from tests.conftest_utils.cli import CaptureOutput, RunCli, run_cli
from tests.conftest_utils.configs import disable_colors
from tests.conftest_utils.logger import reset_all_logger_state
from tests.conftest_utils.paths import (
    examples_no_bakebook_dir,
    examples_no_bakefile_dir,
    examples_simple_dir,
)
from tests.conftest_utils.projects import (
    empty_project_folder,
    empty_project_folder_no_inline,
    isolated_uv_cache,
    uv_project_folder,
    uv_project_folder_with_deps,
    uv_project_folder_without_dep,
)


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
    old_value = os.environ.get(_BAKE_REINVOKED)
    os.environ[_BAKE_REINVOKED] = "1"
    yield
    if old_value is None:
        os.environ.pop(_BAKE_REINVOKED, None)
    else:
        os.environ[_BAKE_REINVOKED] = old_value


__all__ = [
    "CaptureOutput",
    "RunCli",
    "disable_colors",
    "empty_project_folder",
    "empty_project_folder_no_inline",
    "examples_no_bakebook_dir",
    "examples_no_bakefile_dir",
    "examples_simple_dir",
    "isolated_uv_cache",
    "reset_all_logger_state",
    "run_cli",
    "uv_project_folder",
    "uv_project_folder_with_deps",
    "uv_project_folder_without_dep",
]
