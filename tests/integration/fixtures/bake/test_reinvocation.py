from pathlib import Path

import pytest

from bake.ui import run
from bake.ui.logger import find_log, has_messages_in_logs, parse_pretty_log, strip_ansi
from bake.utils import ENV__BAKE_REINVOKED


def test_reinvocation_actually_switches_python(
    uv_project_folder_with_deps: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reinvoking_msg = "Re-invoking with detected Python:"
    _marker_set_msg = "Re-invocation marker set, skipping Python check"

    monkeypatch.delenv(ENV__BAKE_REINVOKED, raising=False)
    result = run(["bake", "-vv", "test-dep"], cwd=uv_project_folder_with_deps, capture_output=True)
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

    result = run(
        ["bakefile", "-vv"], check=False, cwd=uv_project_folder_with_deps, capture_output=True
    )
    # Exit code 1 because no subcommand provided (shows help)
    assert result.returncode == 1
    logs = parse_pretty_log(result.stderr)
    resolved_bakefile_msg = find_log(logs, "Resolve bakefile path:")
    bakefile_path = Path(resolved_bakefile_msg["bakefile_path"])
    assert "--chdir" in result.stdout and "-C" in result.stdout
    assert bakefile_path.exists()
    assert bakefile_path.is_file()
    assert uv_project_folder_with_deps.as_posix() in bakefile_path.as_posix()
