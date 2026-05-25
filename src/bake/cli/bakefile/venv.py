from pathlib import Path

import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path, is_standalone_bakefile
from bake.ui import console, run_uv
from bake.utils.exceptions import PythonNotFoundError


def _resolve_python_env(bakefile_path) -> Path:
    try:
        python_path = find_python_path(bakefile_path)
    except PythonNotFoundError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
    return python_path.parent.parent


def _handle_existing_venv(venv_path, force: bool) -> None:
    if not venv_path.exists() and not venv_path.is_symlink():
        return

    if force and venv_path.is_symlink():
        venv_path.unlink()
        return

    if venv_path.is_symlink():
        console.error(
            f".venv already exists (symlink to {venv_path.resolve()}). Use --force to overwrite."
        )
    else:
        console.error(".venv already exists (directory). Remove it manually first.")
    raise typer.Exit(code=1)


def venv(
    ctx: Context,
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .venv symlink"),
) -> None:
    """Ensure .venv exists in the repo root.

    For PEP 723 standalone bakefiles (inline script metadata):
    symlinks .venv to the uv-managed environment (located
    in the uv cache directory). Use --force to replace an
    existing symlink.

    For standard Python projects (pyproject.toml):
    runs ``uv sync`` to create/update .venv with project
    dependencies.
    """
    bakefile_path = ctx.obj.bakefile_path
    if bakefile_path is None or not bakefile_path.exists():
        console.error("Bakefile not found.")
        raise typer.Exit(code=1)
    venv_path = bakefile_path.parent / ".venv"

    if is_standalone_bakefile(bakefile_path):
        env_dir = _resolve_python_env(bakefile_path)
        _handle_existing_venv(venv_path, force)
        venv_path.symlink_to(env_dir)
        console.success(f"Linked .venv -> {env_dir}")
    else:
        run_uv(["sync"], check=True, cwd=bakefile_path.parent)
        console.success(f".venv created at {venv_path}")
