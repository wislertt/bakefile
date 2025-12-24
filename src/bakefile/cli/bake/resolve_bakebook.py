import importlib.util
import os
import pathlib
import sys

import typer

MODULE_NAME = "bakefile"


def change_directory(path: str) -> None:
    """Change to specified directory after validation."""
    dir_path = pathlib.Path(path)
    if not dir_path.exists():
        typer.echo(f"Directory not found: {path}", err=True)
        raise SystemExit(1)
    if not dir_path.is_dir():
        typer.echo(f"Not a directory: {path}", err=True)
        raise SystemExit(1)
    os.chdir(dir_path)


def validate_file_name(file_name: str) -> None:
    """Validate file_name is a filename (not a path) and ends with .py."""
    if "/" in file_name or "\\" in file_name:
        typer.echo(f"File name must not contain path separators: {file_name}", err=True)
        raise SystemExit(1)
    if not file_name.endswith(".py"):
        typer.echo(f"File name must end with .py: {file_name}", err=True)
        raise SystemExit(1)


def resolve_file_path(file_name: str) -> pathlib.Path:
    """Resolve file path relative to current directory."""
    path = pathlib.Path.cwd() / file_name
    if not path.exists():
        typer.echo(f"File not found: {file_name}", err=True)
        raise SystemExit(1)
    return path


def load_module(path: pathlib.Path) -> object:
    """Load Python module from file path."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
    if spec is None or spec.loader is None:
        typer.echo(f"Failed to load: {path}", err=True)
        raise SystemExit(1)

    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def get_bakebook(module: object, bakebook_name: str, path: pathlib.Path) -> str:
    """Retrieve bakebook object from module."""
    if not hasattr(module, bakebook_name):
        typer.echo(f"No '{bakebook_name}' found in {path}", err=True)
        raise SystemExit(1)
    return getattr(module, bakebook_name)


def resolve_bakebook(file_name: str, bakebook_name: str, chdir: str | None = None) -> str:
    """Load a bakefile and retrieve a bakebook object.

    Args:
        file_name: Name of the .py file (must end with .py, no path separators)
        bakebook_name: Name of the bakebook object to retrieve
        chdir: Optional directory to change to before loading

    Returns:
        The bakebook object value

    Raises:
        SystemExit(1): If any validation or loading step fails
    """
    if chdir:
        change_directory(chdir)

    validate_file_name(file_name)
    path = resolve_file_path(file_name)
    module = load_module(path)
    return get_bakebook(module=module, bakebook_name=bakebook_name, path=path)
