import importlib
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import pytest

from bake.cli.common import reinvocation
from bake.cli.common.reinvocation import _reinvoke_with_detected_python
from bake.utils import ENV__BAKE_REINVOKED, settings


class SubprocessCall(NamedTuple):
    args: list[str]
    env: dict[str, str]


@pytest.fixture
def subprocess_mock(monkeypatch: pytest.MonkeyPatch):
    """Mock subprocess.run to capture calls and prevent actual execution."""
    calls = []

    def fake_run(args, env=None):
        calls.append(SubprocessCall(args=args, env=env or {}))
        return type("CompletedProcess", (), {"returncode": 0})()

    monkeypatch.setattr("bake.cli.common.reinvocation.subprocess.run", fake_run)
    return calls


@pytest.mark.parametrize(
    "marker_set, detected_python, current_python, should_reinvoke",
    [
        # Marker already set - skip reinvocation
        (True, Path("/venv/bin/python"), Path("/usr/bin/python3"), False),
        # Marker not set, Python differs - should reinvoke
        (False, Path("/venv/bin/python"), Path("/usr/bin/python3"), True),
        # Marker not set, Python same - skip reinvocation
        (False, Path("/usr/bin/python3"), Path("/usr/bin/python3"), False),
    ],
)
def test_reinvoke_with_detected_python(
    marker_set: bool,
    detected_python: Path,
    current_python: Path,
    should_reinvoke: bool,
    subprocess_mock: list[SubprocessCall],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if marker_set:
        monkeypatch.setenv(ENV__BAKE_REINVOKED, "1")
    else:
        monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    importlib.reload(settings)
    importlib.reload(reinvocation)

    with (
        patch("bake.manage.find_python.find_python_path", return_value=detected_python),
        patch("sys.executable", str(current_python)),
    ):
        if should_reinvoke:
            with pytest.raises(SystemExit) as exc_info:
                _reinvoke_with_detected_python(Path("bakefile.py"), cli_module="bake.cli.bake")
            assert exc_info.value.code == 0
        else:
            _reinvoke_with_detected_python(Path("bakefile.py"), cli_module="bake.cli.bake")

    assert len(subprocess_mock) == (1 if should_reinvoke else 0)

    if should_reinvoke:
        call = subprocess_mock[0]
        assert call.args[0] == str(detected_python)
        assert "-m" in call.args
        assert "bake.cli.bake" in call.args
        assert call.env.get(ENV__BAKE_REINVOKED) == "1"


def test_reinvoke_graceful_degradation_on_error(
    subprocess_mock: list[SubprocessCall],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that errors in find_python_path don't crash the process."""
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    importlib.reload(settings)
    importlib.reload(reinvocation)

    with patch("bake.manage.find_python.find_python_path", side_effect=Exception("Failed")):
        _reinvoke_with_detected_python(Path("bakefile.py"), cli_module="bake.cli.bake")

    assert len(subprocess_mock) == 0


def test_reinvoke_keyboard_interrupt_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that KeyboardInterrupt during subprocess.run exits with code 130 (SIGINT)."""
    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    importlib.reload(settings)
    importlib.reload(reinvocation)

    def fake_run_raises_keyboard_interrupt(args, env=None):
        _ = args, env
        raise KeyboardInterrupt()

    with (
        patch("bake.manage.find_python.find_python_path", return_value=Path("/venv/bin/python")),
        patch("sys.executable", "/usr/bin/python3"),
        patch("bake.cli.common.reinvocation.subprocess.run", fake_run_raises_keyboard_interrupt),
    ):
        with pytest.raises(SystemExit) as exc_info:
            _reinvoke_with_detected_python(Path("bakefile.py"), cli_module="bake.cli.bake")
        assert exc_info.value.code == 130  # Standard SIGINT exit code (128 + 2)
