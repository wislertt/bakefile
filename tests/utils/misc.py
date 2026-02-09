"""Miscellaneous test utilities - context, logger, flaky, paths, string helpers."""

import sys
from functools import wraps
from pathlib import Path

import click
import loguru
import pytest

from bake import Context
from bake.cli.common.obj import BakefileObject
from bake.ui.logger.utils import reset_all_logging_states
from bake.utils.settings import bake_settings


class SimpleTestCommand(click.Command):
    """Minimal click.Command for testing Context."""

    def __init__(self):
        super().__init__(
            name="test",
            callback=lambda: None,
        )


@pytest.fixture
def mock_ctx(tmp_path: Path):
    obj = BakefileObject(
        chdir=tmp_path,
        file_name="bakefile.py",
        bakebook_name="bakebook",
        dry_run=True,
        verbosity=0,
    )

    command = SimpleTestCommand()
    ctx = Context(command=command, obj=obj, info_name="test")

    return ctx


@pytest.fixture(scope="function", autouse=True)
def reset_all_logger_state():
    yield
    loguru.logger.remove()
    reset_all_logging_states()


def _flaky_on_ci(platform: str, max_retries: int = 5):
    """Internal decorator for flaky tests on specific platform CI."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            is_target_platform = sys.platform == platform

            if not (is_target_platform and bake_settings.ci):
                return func(*args, **kwargs)

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except AssertionError:
                    if attempt == max_retries - 1:
                        raise
            return None

        return wrapper

    return decorator


def flaky_on_macos_ci(max_retries: int = 5):
    """Decorator for flaky tests on macOS CI."""
    return _flaky_on_ci("darwin", max_retries)


def flaky_on_windows_ci(max_retries: int = 5):
    """Decorator for flaky tests on Windows CI."""
    return _flaky_on_ci("win32", max_retries)


@pytest.fixture(scope="session")
def examples_simple_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "simple"


@pytest.fixture(scope="session")
def examples_python_package_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "python-package"


def remove_whitespace(s: str) -> str:
    return "".join(s.split())
