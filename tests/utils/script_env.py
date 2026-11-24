import shutil
from pathlib import Path

from bake.manage.find_python import _find_bakefile_python
from bake.ui import run_uv
from bake.utils.constants import DEFAULT_FILE_NAME

_PEP723_MARKER = "# /// script"


def _uv_environments_dir() -> Path | None:
    result = run_uv(["cache", "dir"], check=False, echo=False)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()) / "environments-v2"


def _standalone_bakefiles(root: Path) -> list[Path]:
    candidates = [root / DEFAULT_FILE_NAME, *root.glob(f"*/{DEFAULT_FILE_NAME}")]
    return [p for p in candidates if p.is_file() and _PEP723_MARKER in p.read_text()]


def remove_script_env(bakefile_path: Path, environments_dir: Path) -> None:
    python_path = _find_bakefile_python(bakefile_path)
    if python_path is None:
        return
    env_dir = python_path.parent.parent
    # Guard: only ever delete a direct child of the uv cache's script-env folder
    if env_dir.parent.resolve() != environments_dir.resolve():
        return
    shutil.rmtree(env_dir, ignore_errors=True)


def remove_script_envs_under(root: Path) -> None:
    bakefiles = _standalone_bakefiles(root)
    if not bakefiles:
        return
    environments_dir = _uv_environments_dir()
    if environments_dir is None or not environments_dir.is_dir():
        return
    for bakefile_path in bakefiles:
        remove_script_env(bakefile_path, environments_dir)
