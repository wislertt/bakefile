"""Miscellaneous test utilities - context, logger, flaky, paths, string helpers."""

import contextlib
import sys
from functools import wraps
from pathlib import Path

import click
import keyring
import loguru
import pytest
from keyring.errors import KeyringError

from bake import Context
from bake.cli.common.obj import BakefileObject
from bake.ui.logger.utils import reset_all_logging_states
from bake.utils.settings import bake_settings


@pytest.fixture(scope="function", autouse=True)
def auto_cleanup_keyring(monkeypatch: pytest.MonkeyPatch):
    """Automatically track and cleanup all keyring entries created during test.

    Monkey patches keyring.set_password to track all (service, username) pairs,
    then deletes them after the test completes.
    """
    registered_keys: list[tuple[str, str]] = []
    keyring_set_password = keyring.set_password

    def tracked_set_password(service: str, username: str, password: str) -> None:
        registered_keys.append((service, username))
        return keyring_set_password(service, username, password)

    monkeypatch.setattr(keyring, "set_password", tracked_set_password)

    yield

    for service, username in registered_keys:
        with contextlib.suppress(KeyringError):
            keyring.delete_password(service, username)


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


def _has_keyring_backend() -> bool:
    """Check if a working keyring backend is available."""
    try:
        # Try to access the keyring - will raise NoKeyringError if no backend
        return keyring.get_keyring() is not None
    except Exception:
        return False


def skip_if_no_keyring(func):
    """Decorator to skip test if no keyring backend is available."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _has_keyring_backend():
            pytest.skip("No keyring backend available")
        return func(*args, **kwargs)

    return wrapper
