# OOP Design for bakefile

Object-oriented patterns for reusable build tasks.

## Core Abstraction

```python
from abc import ABC, abstractmethod
from pathlib import Path

class Task(ABC):
    """Base class for all build tasks."""

    name: str
    description: str | None = None

    @abstractmethod
    def execute(self, cwd: Path) -> int:
        """Execute the task.

        Returns:
            Exit code (0 = success, non-zero = failure)
        """
        pass

    @abstractmethod
    def is_available(self, cwd: Path) -> bool:
        """Check if task can run in current directory."""
        pass

    def pre_run(self, cwd: Path) -> None:
        """Hook before execution."""
        pass

    def post_run(self, cwd: Path, exit_code: int) -> None:
        """Hook after execution."""
        pass
```

## Reusable Task Classes

```python
class ShellCommand(Task):
    """Task that runs a shell command."""

    def __init__(self, name: str, command: str):
        self.name = name
        self.command = command
        self.description = f"Run: {command}"

    def execute(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(
            self.command,
            shell=True,
            cwd=cwd
        )
        return result.returncode

    def is_available(self, cwd: Path) -> bool:
        return True


class PythonTask(Task):
    """Task that runs Python code."""

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code
        self.description = f"Run Python: {code[:50]}..."

    def execute(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "-c", self.code],
            cwd=cwd
        )
        return result.returncode

    def is_available(self, cwd: Path) -> bool:
        # Check if uv is available
        import shutil
        return shutil.which("uv") is not None
```

## Composition over Inheritance

```python
class TaskRunner:
    """Manages and executes tasks."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def register(self, task: Task) -> None:
        """Register a task."""
        self.tasks[task.name] = task

    def run(self, name: str, cwd: Path) -> int:
        """Run a task by name."""
        task = self.tasks.get(name)
        if not task:
            typer.echo(f"Unknown task: {name}", err=True)
            return 1

        if not task.is_available(cwd):
            typer.echo(f"Task not available: {name}", err=True)
            return 1

        task.pre_run(cwd)
        exit_code = task.execute(cwd)
        task.post_run(cwd, exit_code)
        return exit_code
```

## Template Method Pattern

```python
class BaseTestTask(Task):
    """Template for test tasks."""

    def __init__(self, name: str):
        self.name = name
        self.description = "Run tests"

    def execute(self, cwd: Path) -> int:
        # Template method - defines the flow
        self.setup(cwd)
        exit_code = self.run_tests(cwd)
        self.teardown(cwd)
        return exit_code

    def setup(self, cwd: Path) -> None:
        """Hook for setup. Override in subclass."""
        pass

    def run_tests(self, cwd: Path) -> int:
        """Run the actual tests. Override in subclass."""
        raise NotImplementedError

    def teardown(self, cwd: Path) -> None:
        """Hook for teardown. Override in subclass."""
        pass


class PytestTask(BaseTestTask):
    """Pytest implementation."""

    def run_tests(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/"],
            cwd=cwd
        )
        return result.returncode


class RuffTask(BaseTestTask):
    """Ruff linting implementation."""

    def run_tests(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(
            ["uv", "run", "ruff", "check"],
            cwd=cwd
        )
        return result.returncode
```

## Strategy Pattern

```python
class DependencyStrategy(ABC):
    """Strategy for resolving dependencies."""

    @abstractmethod
    def install(self, cwd: Path) -> int:
        pass

    @abstractmethod
    def is_installed(self, cwd: Path) -> bool:
        pass


class UVStrategy(DependencyStrategy):
    """UV dependency strategy."""

    def install(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(["uv", "sync"], cwd=cwd)
        return result.returncode

    def is_installed(self, cwd: Path) -> bool:
        return (cwd / "uv.lock").exists()


class PipStrategy(DependencyStrategy):
    """Pip dependency strategy."""

    def install(self, cwd: Path) -> int:
        import subprocess
        result = subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=cwd)
        return result.returncode

    def is_installed(self, cwd: Path) -> bool:
        return (cwd / "venv").exists()
```

## Factory Pattern

```python
class TaskFactory:
    """Factory for creating tasks."""

    @staticmethod
    def from_config(config: dict) -> Task:
        """Create task from configuration dict."""
        task_type = config.get("type")

        if task_type == "shell":
            return ShellCommand(config["name"], config["command"])
        elif task_type == "python":
            return PythonTask(config["name"], config["code"])
        else:
            raise ValueError(f"Unknown task type: {task_type}")
```

## Best Practices

1. **Favor composition** - Use TaskRunner to compose tasks
2. **Small interfaces** - ABC with minimal methods
3. **Template method** - For shared execution flow
4. **Strategy pattern** - For pluggable algorithms
5. **Factory pattern** - For object creation
6. **Single responsibility** - Each class does one thing
7. **Open/closed principle** - Open for extension, closed for modification
