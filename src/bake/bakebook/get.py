import importlib.util
import logging
import sys
import types
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.abc import Loader
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from bake.manage.find_python import is_standalone_bakefile
from bake.manage.run_uv import run_uv_sync
from bake.ui import console, style
from bake.ui.run import run_uv
from bake.utils.exceptions import BakebookError, BakefileNotFoundError
from bake.utils.settings import bake_settings

if TYPE_CHECKING:
    from bake.bakebook.bakebook import Bakebook

logger = logging.getLogger(__name__)

T = TypeVar("T")


@contextmanager
def prepend_sys_path(path: str) -> Generator[None, None, None]:
    path_existed = path in sys.path
    if not path_existed:
        sys.path.insert(0, path)
    try:
        yield
    finally:
        if not path_existed:
            sys.path.remove(path)


def get_target_dir_path(chdir: Path, create_if_not_exist: bool) -> Path:
    if not chdir.exists():
        if create_if_not_exist:
            chdir.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Directory not found: {chdir}")
            raise BakefileNotFoundError(f"Directory not found: {chdir}")
    if not chdir.is_dir():
        logger.debug(f"Not a directory: {chdir}")
        raise BakefileNotFoundError(f"Not a directory: {chdir}")
    return chdir.resolve()


ResolvedBy = Literal["exact", "walk_up", "global", "global_fallback"]


@dataclass(frozen=True)
class BakefileResolution:
    path: Path
    resolved_by: ResolvedBy
    searched: tuple[Path, ...]
    found: bool
    global_path: Path

    @property
    def is_global(self) -> bool:
        return self.resolved_by in ("global", "global_fallback")

    def not_found_message(self) -> str:
        file_name = self.path.name
        if self.resolved_by == "global":
            return (
                f"Global {file_name} not found: {self.path}\nRun `bakefile -g init` to create it."
            )
        if self.resolved_by == "exact":
            searched = f"Searched in: {self.searched[0]}"
        else:
            searched = f"Searched in: {self.searched[0]} and parent directories"
        global_state = "exists" if self.global_path.is_file() else "not found"
        return f"{file_name} not found.\n{searched}\nGlobal: {self.global_path} ({global_state})"


def get_global_dir_path() -> Path:
    return bake_settings.global_bake_dir.resolve()


def resolve_bakefile_path(
    chdir: Path | None, file_name: str, use_global: bool = False
) -> BakefileResolution:
    global_path = get_global_dir_path() / file_name
    if use_global:
        resolution = BakefileResolution(
            path=global_path,
            resolved_by="global",
            searched=(global_path.parent,),
            found=global_path.is_file(),
            global_path=global_path,
        )
    elif chdir is not None:
        target_dir_path = get_target_dir_path(chdir=chdir, create_if_not_exist=False)
        bakefile_path = target_dir_path / file_name
        resolution = BakefileResolution(
            path=bakefile_path,
            resolved_by="exact",
            searched=(target_dir_path,),
            found=bakefile_path.is_file(),
            global_path=global_path,
        )
    else:
        resolution = _walk_up(start=Path.cwd().resolve(), global_path=global_path)

    logger.debug(
        f"Resolve bakefile path: {resolution.path} ({resolution.resolved_by})",
        extra={"bakefile_path": resolution.path, "resolved_by": resolution.resolved_by},
    )
    return resolution


def _walk_up(start: Path, global_path: Path) -> BakefileResolution:
    file_name = global_path.name
    searched: list[Path] = []
    for directory in (start, *start.parents):
        searched.append(directory)
        candidate = directory / file_name
        if candidate.is_file():
            return BakefileResolution(
                path=candidate,
                resolved_by="walk_up",
                searched=tuple(searched),
                found=True,
                global_path=global_path,
            )
    if global_path.is_file():
        return BakefileResolution(
            path=global_path,
            resolved_by="global_fallback",
            searched=(*searched, global_path.parent),
            found=True,
            global_path=global_path,
        )
    return BakefileResolution(
        path=start / file_name,
        resolved_by="walk_up",
        searched=tuple(searched),
        found=False,
        global_path=global_path,
    )


def retry_load_module_with_uv_sync(
    target_dir_path: Path,
    error: ImportError,
    parent_dir: str,
    loader: Loader,
    module: types.ModuleType,
    dry_run: bool = False,
):
    logger.debug(f"Missing dependency: {error.name}. Running sync...")

    sync_args = ["--frozen"]

    try:
        if is_standalone_bakefile(target_dir_path):
            # Standalone bakefile: use --script flag
            run_uv_sync(
                bakefile_path=target_dir_path,
                cmd=sync_args,
                dry_run=dry_run,
            )
        else:
            # Project-level: use uv sync directly
            sync_args.extend(["--all-groups", "--all-extras"])
            run_uv(
                ("sync", *sync_args),
                cwd=parent_dir,
                capture_output=True,
                stream=True,
                check=True,
                echo=True,
                dry_run=dry_run,
            )
    except Exception as sync_error:
        # Without this, the failure (typer.Exit from check=True) escapes from
        # inside the caller's `except ImportError` handler as a raw traceback.
        # `from None` keeps console output one clean line; details go to DEBUG.
        logger.debug("uv sync failed during bakebook load", exc_info=sync_error)
        error_message = (
            f"Failed to import bakefile: {error}.\n"
            f"Auto 'uv sync' failed. Install the missing dependency "
            f"in your project environment, then retry. (run `bake -vvv <command>` for details)"
        )
        raise BakebookError(error_message) from None

    try:
        loader.exec_module(module)
    except Exception as e:
        error_message = (
            f"Failed get bakebook from: {target_dir_path} even after sync.\n"
            f"{e.__class__.__name__}: {e}"
        )
        logger.debug(error_message)
        console.error(
            "Failed to load bakebook after dependency sync. "
            f"Try running {style.code('uv cache clean')} to resolve potential caching issues."
        )
        raise BakebookError(error_message) from e


def load_module(target_dir_path: Path) -> types.ModuleType:
    if not target_dir_path.exists():
        logger.debug(f"Directory not found: {target_dir_path}")
        raise BakefileNotFoundError(f"Directory not found: {target_dir_path}")

    parent_dir = str(target_dir_path.parent)
    module_name = "bakefile"

    with prepend_sys_path(parent_dir):
        spec = importlib.util.spec_from_file_location(module_name, target_dir_path)
        if spec is None or spec.loader is None:
            logger.debug(f"Failed to load bakebook module from: {target_dir_path}")
            raise BakebookError(f"Failed to load: {target_dir_path}")

        module: types.ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except ImportError as e:
            retry_load_module_with_uv_sync(
                target_dir_path=target_dir_path,
                error=e,
                parent_dir=parent_dir,
                loader=spec.loader,
                module=module,
            )
        except Exception as e:
            error_message = (
                f"Failed get bakebook from: {target_dir_path}.\n{e.__class__.__name__}: {e}"
            )
            logger.debug(error_message)
            raise BakebookError(error_message) from e
        return module


def validate_bakebook(bakebook: Any, bakebook_name: str) -> "Bakebook":
    from bake.bakebook.bakebook import Bakebook

    if not isinstance(bakebook, Bakebook):
        logger.debug(
            f"Invalid bakebook type for '{bakebook_name}': "
            f"expected {Bakebook.__name__}, got {type(bakebook).__name__}"
        )
        raise BakebookError(
            f"Bakebook '{bakebook_name}' must be a {Bakebook.__name__}, "
            f"got {type(bakebook).__name__}"
        )

    return bakebook


def get_bakebook_from_module(
    module: types.ModuleType, bakebook_name: str, target_dir_path: Path
) -> "Bakebook":
    if not hasattr(module, bakebook_name):
        logger.debug(f"Bakebook '{bakebook_name}' not found in {target_dir_path}")
        raise BakebookError(f"No '{bakebook_name}' found in {target_dir_path}")
    bakebook = getattr(module, bakebook_name)
    bakebook = validate_bakebook(bakebook=bakebook, bakebook_name=bakebook_name)
    return bakebook


def get_bakebook_from_target_dir_path(
    target_dir_path: Path,
    bakebook_name: str,
) -> "Bakebook":
    module = load_module(target_dir_path=target_dir_path)
    bakebook = get_bakebook_from_module(
        module=module, bakebook_name=bakebook_name, target_dir_path=target_dir_path
    )
    logger.debug(f"Successfully retrieved bakebook '{bakebook_name}' from {target_dir_path}")
    return bakebook
