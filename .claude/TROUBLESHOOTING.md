# TROUBLESHOOTING.md

**Known issues and gotchas for bakefile**

## Common Errors and Fixes

### Bakebook Not Found Warning

**Symptom:**

```
⚠️  Bakebook `bakebook` not found in `bakefile.py`
Searched in: /path/to/project
```

**Cause:** The bakefile.py doesn't contain a variable with the expected bakebook name.

**Solutions:**

1. Check that your `bakefile.py` defines a `bakebook` variable:

```python
import typer

bakebook = typer.Typer()  # Must be named 'bakebook' by default

@bakebook.command()
def build():
    ...
```

2. If using a different variable name, specify it with `-b`:

```bash
bake -b my_bakebook_name build
```

3. Ensure the file is in the expected location (default: current directory):

```bash
bake -C /path/to/project build
```

### File Name Validation Error

**Symptom:**

```
Error: File name must not contain path separators: tasks/bakefile.py
```

or

```
Error: File name must end with .py: bakefile
```

**Cause:** The `--file-name` or `-f` option must be a filename only, not a path, and must end with `.py`.

**Solution:**

```bash
# Bad
bake -f tasks/bakefile.py build

# Good - use -C for directory, -f for filename
bake -C tasks -f bakefile.py build
```

### Bakebook Type Error

**Symptom:**

```
Error: Bakebook 'bakebook' must be a Typer, got dict
```

**Cause:** The bakebook variable is not a `typer.Typer` instance.

**Solution:**

```python
# Bad
bakebook = {"commands": [...]}

# Good
import typer
bakebook = typer.Typer()
```

### Module Import Errors

**Symptom:**

```
Error: Failed to load: /path/to/bakefile.py
```

**Cause:** The bakefile.py has syntax errors or cannot be imported as a Python module.

**Solutions:**

1. Check the file for syntax errors:

```bash
python -m py_compile bakefile.py
```

2. Ensure the file is valid Python:

```bash
python bakefile.py  # Should not have import/syntax errors
```

3. Check file permissions:

```bash
ls -la bakefile.py
```

## Setup Issues

### bake Command Not Found

**Symptom:**

```
bash: bake: command not found
```

**Cause:** The bakefile package is not installed or not in PATH.

**Solutions:**

1. Install the package in development mode:

```bash
uv pip install -e .
# or
pip install -e .
```

2. Check the installation:

```bash
pip show bakefile
```

3. If using UV, ensure you're in the correct environment:

```bash
uv pip list | grep bakefile
```

### Version Shows 0.0.0

**Symptom:**

```
bake --version
# Output: bake 0.0.0
```

**Cause:** The package is not properly installed (version comes from package metadata).

**Solution:**

```bash
# Reinstall the package
uv pip install -e .
# or
pip install -e .
```

## Debugging Tips

### Enable Verbose Output

To see more details about what's happening:

```bash
# Check what bakebook is being loaded
bake -C /path/to/project --help

# Use with custom file name
bake -C /path/to/project -f custom.py --help
```

### Check Bakebook Loading

The `get_bakebook()` method uses `contextlib.suppress(BakebookError)`, so errors loading the bakebook are silently ignored. To debug bakebook loading issues:

1. Check that the file exists:

```bash
ls -la bakefile.py
```

2. Try importing manually:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("bakefile", "bakefile.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(dir(module))  # Should show 'bakebook'
```

### Disable Colors for Debugging

If color output is causing issues:

```bash
NO_COLOR=1 bake build
```

## Known Limitations

### No Bakebook Found is Non-Fatal

When `bake` runs but no bakebook is found, it shows a warning but continues. This is by design - the CLI will still run but won't have any user commands available.

### Module Caching

The bakebook module is loaded with a fixed module name (`"bakefile"`) and cached in `sys.modules`. This means:

- Only one bakebook can be loaded per Python process
- If you need to load multiple bakebooks, use separate subprocess invocations

### Path Separator Validation

File names are validated to not contain path separators (`/` or `\\`). Use the `-C` option to change directories instead.

## Workarounds

### Multiple Bakebooks in Same Directory

If you need multiple bakebook definitions in the same directory:

```python
# tasks.py
import typer

bakebook = typer.Typer()
dev_book = typer.Typer()

@bakebook.command()
def build():
    ...

@dev_book.command()
def lint():
    ...
```

Run with:

```bash
bake -f tasks.py build       # Uses default 'bakebook'
bake -f tasks.py -b dev_book lint  # Uses 'dev_book'
```

### Conditional Commands

For commands that should only be available in certain environments:

```python
import typer
import os

bakebook = typer.Typer()

if os.environ.get("CI"):
    @bakebook.command()
    def ci_build():
        typer.echo("Running CI build...")
```

### Override Existing Bakefile

The `bakefile init` command supports `--force` to overwrite existing files:

```bash
bakefile init --force
```

This will overwrite the existing `bakefile.py` with the sample template.
