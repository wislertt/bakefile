import importlib.util
import os
import pathlib
import sys
import types
from typing import Any, TypeVar

import typer

from bakefile.exceptions import BakebookError

T = TypeVar("T")


def change_directory(path: str) -> None:
    if not path or not path.strip():
        raise BakebookError("Directory path cannot be empty")
    dir_path = pathlib.Path(path)
    if not dir_path.exists():
        raise BakebookError(f"Directory not found: {path}")
    if not dir_path.is_dir():
        raise BakebookError(f"Not a directory: {path}")
    os.chdir(dir_path)


def validate_file_name(file_name: str) -> bool:
    if "/" in file_name or "\\" in file_name:
        raise BakebookError(f"File name must not contain path separators: {file_name}")
    if not file_name.endswith(".py"):
        raise BakebookError(f"File name must end with .py: {file_name}")
    return True


def resolve_file_path(file_name: str) -> pathlib.Path:
    path = pathlib.Path.cwd() / file_name
    if not path.exists():
        raise BakebookError(f"File not found: {file_name}")
    return path


def load_module(path: pathlib.Path) -> types.ModuleType:
    module_name = "bakefile"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise BakebookError(f"Failed to load: {path}")

    module: types.ModuleType = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Update this is lowest python support is >= 3.12
# Use a generic type parameter for this function instead of a "TypeVar".
def validate_bakebook(bakebook: Any, bakebook_name: str, expected_type: type[T]) -> T:
    """Validate bakebook is of expected type and return it.

    Parameters
    ----------
    bakebook : Any
        The bakebook object to validate
    bakebook_name : str
        Name of the bakebook variable (for error messages)
    expected_type : type[T]
        The expected type (e.g., typer.Typer)

    Returns
    -------
    T
        The validated bakebook

    Raises
    ------
    BakebookError
        If bakebook is not of expected type
    """
    if not isinstance(bakebook, expected_type):
        raise BakebookError(
            f"Bakebook '{bakebook_name}' must be a {expected_type.__name__}, "
            f"got {type(bakebook).__name__}"
        )

    return bakebook


def get_bakebook(module: types.ModuleType, bakebook_name: str, path: pathlib.Path) -> typer.Typer:
    if not hasattr(module, bakebook_name):
        raise BakebookError(f"No '{bakebook_name}' found in {path}")
    bakebook = getattr(module, bakebook_name)
    bakebook = validate_bakebook(
        bakebook=bakebook, bakebook_name=bakebook_name, expected_type=typer.Typer
    )
    return bakebook


def resolve_bakebook(file_name: str, bakebook_name: str, chdir: str | None = None) -> typer.Typer:
    if chdir:
        change_directory(chdir)

    validate_file_name(file_name)
    path = resolve_file_path(file_name)
    module = load_module(path)
    return get_bakebook(module=module, bakebook_name=bakebook_name, path=path)
