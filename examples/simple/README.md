# Simple Bakefile Example

A minimal bakefile demonstrating basic command definitions.

## Reproduce This Example

```bash
# Initialize a new bakefile with PEP 723 inline metadata
bakefile init --inline

# For development: use the local bakefile package in editable mode
bakefile add "bakefile @ ../.." --editable
```

## Usage

```bash
# Show available commands
bake --help

# Run the foo command
bake foo

# Run the hello command
bake hello

# Upgrade all dependencies for bakefile.py
bake update
```
