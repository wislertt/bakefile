# Packaging

Patterns for packaging Python tools with UV and pyproject.toml.

## pyproject.toml Structure

```toml
[project]
name = "bakefile"
version = "0.0.0"  # Managed by git tags
description = "Python-based build system with OOP reusability"
readme = "README.md"
authors = [
    {name = "Your Name", email = "you@example.com"}
]
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "ty>=0.0.5",
]

[project.scripts]
bake = "bakefile.cli:app"
bakefile = "bakefile.cli:meta_app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

## CLI Entry Points

```python
# src/bakefile/cli.py
import typer

app = typer.Typer(help="bake - run tasks from bakefile.py")


@app.command()
def run(task: str):
    """Run a task."""
    pass


meta_app = typer.Typer(help="bakefile - manage bakefile")


@meta_app.command()
def init():
    """Initialize bakefile in current directory."""
    pass
```

## Package Structure

```
bakefile/
├── pyproject.toml
├── README.md
├── src/
│   └── bakefile/
│       ├── __init__.py
│       ├── cli.py
│       └── core/
│           └── ...
└── tests/
    └── test_bakefile.py
```

## Building

```bash
# Build wheel
uv build

# Build for distribution
uv build --wheel
```

## Publishing

```bash
# Publish to TestPyPI
uv publish --index test-pypi

# Publish to PyPI
uv publish
```

## Version Management

```bash
# Tag a version
git tag v0.1.0
git push origin v0.1.0

# Version is read from git tag in CI/CD
```

## Dependency Groups

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]

docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
]

test = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]
```

## Installing from Source

```bash
# Install in editable mode
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"
```

## Type Checking

```toml
[tool.ty]
# Enable strict mode
enable = true
# Check all files
paths = ["src"]

# Or use pyright
[tool.pyright]
typeCheckingMode = "strict"
```

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = []

[tool.ruff.lint.isort]
known-first-party = ["bakefile"]
```

## Best Practices

1. **Use src layout** - `src/bakefile/` not `bakefile/`
2. **pyproject.toml only** - No setup.py or setup.cfg
3. **Type hints** - All public functions
4. **Entry points** - Use `[project.scripts]`
5. **Version from git** - Don't hardcode in file
6. **Dependencies** - Pin minimum versions
