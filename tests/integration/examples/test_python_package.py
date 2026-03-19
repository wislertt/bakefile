from pathlib import Path

from bake.ui import run
from bake.ui.logger import strip_ansi
from tests.utils.fixtures import get_project_env


def test_python_package(examples_python_package_dir: Path) -> None:
    env = get_project_env(examples_python_package_dir)

    result = run(
        ["bake", "setup-dev"],
        cwd=examples_python_package_dir,
        env=env,
        check=False,
        capture_output=True,
    )
    stderr = strip_ansi(result.stderr).strip()
    assert result.returncode == 0
    assert "All versions already on latest supported patch release" in stderr
    assert "Installed" in stderr
    assert "packages" in stderr

    result = run(
        ["bake", "update"],
        cwd=examples_python_package_dir,
        env=env,
        capture_output=True,
    )
    stderr = strip_ansi(result.stderr).strip()
    assert result.returncode == 0
    assert "Resolved" in stderr
    assert "packages" in stderr

    result = run(
        ["bake", "assert-setup-dev"],
        cwd=examples_python_package_dir,
        env=env,
        capture_output=True,
    )
    assert result.returncode == 0

    stdout = strip_ansi(result.stdout).strip()
    stderr = strip_ansi(result.stderr).strip()

    # Verify lint runs successfully
    assert "prettier" in stderr and "ruff" in stderr

    # Check that .venv path appears in output (may be line-wrapped)
    assert ".venv" in stdout and examples_python_package_dir.name in stdout

    # assert tools
    assert "✅ [SUCCESS] bun" in stderr
    assert "✅ [SUCCESS] uv" in stderr
    assert "✅ [SUCCESS] bakefile" in stderr
    assert "✅ [SUCCESS] python" in stderr
    assert "✅ [SUCCESS] pre-commit" in stderr

    # assert lint
    assert "All checks passed!" in stdout
    assert "No dependency issues found." in stderr

    # assert test
    assert "test session starts" in stdout
    assert "tests coverage" in stdout
    assert " passed in " in stdout
