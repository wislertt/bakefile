from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import pytest

from bake.cli.bake.reinvocation import _reinvoke_with_detected_python
from bake.ui import run
from bake.ui.logger import find_log, has_messages_in_logs, parse_pretty_log, strip_ansi
from bake.utils.env import _BAKE_REINVOKED


class ExecvCall(NamedTuple):
    python: Path
    args: list[str]


@pytest.fixture
def execv_mock(monkeypatch: pytest.MonkeyPatch):
    """Mock os.execve to capture calls instead of replacing process."""
    calls = []

    def fake_execve(path, args, _env):
        calls.append(ExecvCall(python=Path(path), args=args))

    monkeypatch.setattr("os.execve", fake_execve)
    return calls


@pytest.mark.parametrize(
    "marker_set, detected_python, current_python, should_execv",
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
    should_execv: bool,
    execv_mock: list[ExecvCall],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _reinvoke_with_detected_python behavior with different scenarios."""
    if marker_set:
        monkeypatch.setenv(_BAKE_REINVOKED, "1")
    else:
        monkeypatch.delenv(_BAKE_REINVOKED, raising=False)

    with (
        patch("bake.manage.find_python.find_python_path", return_value=detected_python),
        patch("sys.executable", str(current_python)),
    ):
        _reinvoke_with_detected_python(Path("bakefile.py"))

    assert len(execv_mock) == (1 if should_execv else 0)

    if should_execv:
        call = execv_mock[0]
        assert call.python == detected_python
        assert call.args[0] == str(detected_python)
        assert "-m" in call.args
        assert "bake.cli.bake" in call.args


def test_reinvoke_graceful_degradation_on_error(
    execv_mock: list[ExecvCall],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that errors in find_python_path don't crash the process."""
    monkeypatch.delenv(_BAKE_REINVOKED, raising=False)

    with patch("bake.manage.find_python.find_python_path", side_effect=Exception("Failed")):
        _reinvoke_with_detected_python(Path("bakefile.py"))

    assert len(execv_mock) == 0


# TODO: REALLY SLOW
@pytest.mark.integration
def test_reinvocation_actually_switches_python(
    uv_project_folder_with_deps: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _reinvoking_msg = "Re-invoking bake with detected Python:"
    _marker_set_msg = "Re-invocation marker set, skipping Python check"

    monkeypatch.delenv(_BAKE_REINVOKED, raising=False)
    result = run(["bake", "-vv", "test-dep"], check=False, cwd=uv_project_folder_with_deps)
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

    result = run(["bakefile", "-vv"], check=False, cwd=uv_project_folder_with_deps)
    # Exit code 1 because no subcommand provided (shows help)
    assert result.returncode == 1
    logs = parse_pretty_log(result.stderr)
    resolved_bakefile_msg = find_log(logs, "Resolve bakefile path:")
    bakefile_path = Path(resolved_bakefile_msg["bakefile_path"])
    assert "--chdir" in result.stdout and "-C" in result.stdout
    assert bakefile_path.exists()
    assert bakefile_path.is_file()
    assert uv_project_folder_with_deps.as_posix() in bakefile_path.as_posix()
