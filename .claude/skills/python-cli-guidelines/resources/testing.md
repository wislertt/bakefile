# Testing CLI Tools

Patterns for testing Python CLI tools with pytest.

## Testing Typer Commands

```python
import typer
from typer.testing import CliRunner

app = typer.Typer()

@app.command()
def hello(name: str = "World"):
    typer.echo(f"Hello {name}!")

# Test
runner = CliRunner()

def test_hello_default():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Hello World!" in result.stdout

def test_hello_with_name():
    result = runner.invoke(app, ["--name", "Claude"])
    assert result.exit_code == 0
    assert "Hello Claude!" in result.stdout
```

## Testing Task Execution

```python
from pathlib import Path
from bakefile.core import ShellCommand

def test_shell_command_success(tmp_path: Path):
    """Test successful shell command execution."""
    task = ShellCommand("test", "echo hello")
    exit_code = task.execute(tmp_path)
    assert exit_code == 0

def test_shell_command_failure(tmp_path: Path):
    """Test failed shell command execution."""
    task = ShellCommand("test", "false")  # always returns 1
    exit_code = task.execute(tmp_path)
    assert exit_code == 1
```

## Mocking Subprocess

```python
from unittest.mock import patch, MagicMock
import subprocess

def test_task_with_mocked_subprocess():
    """Test task with mocked subprocess."""
    task = ShellCommand("test", "echo hello")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        exit_code = task.execute(Path("/tmp"))

        assert exit_code == 0
        mock_run.assert_called_once()
```

## Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    (tmp_path / "bakefile.py").write_text("# test bakefile")
    return tmp_path

@pytest.fixture
def runner():
    """CliRunner fixture."""
    return CliRunner()
```

## Testing Pydantic Models

```python
from pydantic import ValidationError
import pytest

def test_valid_task_config():
    """Test valid task configuration."""
    config = TaskConfig(name="test", command="pytest")
    assert config.name == "test"

def test_invalid_task_config():
    """Test invalid task configuration."""
    with pytest.raises(ValidationError):
        TaskConfig(name="", command="pytest")  # empty name

def test_task_names_must_be_unique():
    """Test that task names must be unique."""
    with pytest.raises(ValidationError):
        BakefileConfig(
            project_name="test",
            tasks=[
                TaskConfig(name="test", command="echo 1"),
                TaskConfig(name="test", command="echo 2"),
            ]
        )
```

## Testing File I/O

```python
def test_load_bakefile(tmp_path: Path):
    """Test loading bakefile from disk."""
    bakefile_path = tmp_path / "bakefile.py"
    bakefile_path.write_text('name: "test"')

    config = load_bakefile(bakefile_path)
    assert config.name == "test"

def test_load_bakefile_not_found(tmp_path: Path):
    """Test loading non-existent bakefile."""
    with pytest.raises(FileNotFoundError):
        load_bakefile(tmp_path / "missing.py")
```

## Testing Error Handling

```python
def test_invalid_yaml(tmp_path: Path):
    """Test handling of invalid YAML."""
    (tmp_path / "bakefile.py").write_text("invalid: [yaml")

    with pytest.raises(yaml.YAMLError):
        load_bakefile(tmp_path / "bakefile.py")

def test_task_not_available():
    """Test running unavailable task."""
    task = PythonTask("test", "import nonexistent")
    assert not task.is_available(Path("/tmp"))
```

## Coverage

```bash
# Run with coverage
uv run pytest --cov=src --cov-report=html

# View HTML report
open htmlcov/index.html
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_cli.py              # CLI command tests
├── test_tasks.py            # Task class tests
├── test_config.py           # Pydantic model tests
└── test_integration.py      # End-to-end tests
```

## Best Practices

1. **Use CliRunner** - For testing Typer commands
2. **Mock subprocess** - Avoid running real commands
3. **Use tmp_path** - For file operations
4. **Test failures** - Not just success cases
5. **Fixtures** - For common setup
6. **Coverage** - Aim for >80%
7. **Integration tests** - Test full workflows
