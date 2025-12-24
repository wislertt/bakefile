# UV Integration

Patterns for using UV with bakefile for automatic Python environment resolution.

## UV Commands

```bash
# Run commands in project environment
uv run pytest
uv run ruff check

# Run with specific Python version
uv run --python 3.12 pytest

# Run scripts directly
uv run python script.py
```

## Auto-Environment Detection

UV automatically detects the Python environment based on:

1. `.python-version` file
2. `pyproject.toml` requires-python
3. Project virtual environment (`.venv`)

## bakefile Integration

```python
import subprocess
from pathlib import Path

def run_with_uv(command: list[str], cwd: Path) -> int:
    """Run command using UV for environment resolution."""
    result = subprocess.run(
        ["uv", "run"] + command,
        cwd=cwd
    )
    return result.returncode

# Example task
class TestTask(Task):
    """Run tests using UV."""
    name = "test"
    description = "Run tests with UV"

    def execute(self, cwd: Path) -> int:
        return run_with_uv(["pytest"], cwd)
```

## UV Script Execution

```python
def execute_python(code: str, cwd: Path) -> int:
    """Execute Python code using UV."""
    result = subprocess.run(
        ["uv", "run", "python", "-c", code],
        cwd=cwd
    )
    return result.returncode
```

## Dependency Installation

```python
def install_dependencies(cwd: Path) -> int:
    """Install dependencies using UV."""
    result = subprocess.run(
        ["uv", "sync"],
        cwd=cwd
    )
    return result.returncode
```

## Python Version Pinning

Create `.python-version`:

```
3.11
```

Or in `pyproject.toml`:

```toml
[project]
requires-python = ">=3.11"
```

## Virtual Environment Management

```bash
# Create .venv
uv venv

# Sync dependencies
uv sync

# Add dependency
uv add pytest

# Add dev dependency
uv add --dev ruff
```

## UV in bakefile.py

When user writes `bakefile.py`, UV should handle environment:

```python
# In user's bakefile.py
from bakefile import Task, run

class TestTask(Task):
    name = "test"

    def execute(self, cwd):
        # UV automatically finds the right Python
        return run(["pytest"], cwd=cwd)
```

## Detecting UV Availability

```python
import shutil

def has_uv() -> bool:
    """Check if UV is available."""
    return shutil.which("uv") is not None

def ensure_uv():
    """Ensure UV is installed."""
    if not has_uv():
        raise RuntimeError(
            "UV is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
```

## Fallback to System Python

```python
def run_command(command: list[str], cwd: Path, use_uv: bool = True) -> int:
    """Run command with UV or fallback to system Python."""
    if use_uv and has_uv():
        return subprocess.run(["uv", "run"] + command, cwd=cwd).returncode
    else:
        return subprocess.run(command, cwd=cwd).returncode
```

## UV Cache Location

UV caches downloads and builds in:

- macOS: `~/Library/Caches/uv`
- Linux: `~/.cache/uv`
- Windows: `%LOCALAPPDATA%\uv\cache`

## Best Practices

1. **Always use uv run** - For project commands
2. **Lock file** - Commit `uv.lock` for reproducibility
3. **.python-version** - Pin Python version
4. **Check for UV** - Provide helpful error if missing
5. **Graceful fallback** - Allow system Python if UV unavailable
6. **Sync before run** - Ensure dependencies installed
