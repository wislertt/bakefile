# Python Package with Bakefile

A Python package example using bakefile for task automation.

## Reproduce This Example

```bash
# Initialize a new Python package
uv init --package --no-workspace

# Add bakefile (uses published version from PyPI)
uv add bakefile[lib]

# For development: use bakefile from local repo (../.. = parent directory relative to examples/python-package)
# uv add "bakefile[lib] @ ../.." --editable
```

Update `pyproject.toml`:

```toml
[dependency-groups]
dev = [
  "deptry>=0.24.0",
  "pre-commit>=4.5.1",
  "pytest-cov>=7.0.0",
  "pytest>=9.0.2",
  "toml-sort>=0.24.3"
]

[tool.deptry.package_module_name_map]
bakefile = ["bake", "bakelib"]
```

Copy `bakefile.py` and `tests/` from this example directory.

## Usage

```bash
# Show available commands
bake --help

# Run the hello command
bake hello

# Setup development environment
bake setup-dev

# Assert development environment setup
bake assert-setup-dev

# Run linters and formatters
bake lint

# Run unit tests
bake test

# Upgrade all dependencies for bakefile.py
bake update
```
