import os
from pathlib import Path

import pytest

from bake.utils.env import _BAKE_REINVOKED


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
    old_value = os.environ.get(_BAKE_REINVOKED)
    os.environ[_BAKE_REINVOKED] = "1"
    yield
    if old_value is None:
        os.environ.pop(_BAKE_REINVOKED, None)
    else:
        os.environ[_BAKE_REINVOKED] = old_value
