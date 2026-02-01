import os
from pathlib import Path

import pytest

from bake.utils.settings import bake_settings


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
    old_value = bake_settings.bake_reinvoked
    bake_settings.bake_reinvoked = True
    yield
    bake_settings.bake_reinvoked = old_value
