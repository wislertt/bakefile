import os
import sys
from pathlib import Path

from bake.ui import console, style
from bake.utils.settings import bake_settings

ENVIRONMENTS_BUCKET_PREFIX = "environments-v"


def uv_cache_dir() -> Path | None:
    # Mirrors uv's own lookup without a ~15 ms `uv cache dir` call; misses `cache-dir` in uv.toml
    if cache_dir := os.environ.get("UV_CACHE_DIR"):
        return Path(cache_dir)
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        return Path(local_app_data) / "uv" / "cache" if local_app_data else None
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home and Path(xdg_cache_home).is_absolute():
        return Path(xdg_cache_home) / "uv"
    return Path.home() / ".cache" / "uv"


def _subdirs(path: Path | str, prefix: str) -> list[str]:
    try:
        with os.scandir(path) as entries:
            return [e.path for e in entries if e.name.startswith(prefix) and e.is_dir()]
    except OSError:
        return []


def count_script_envs(cache_dir: Path, stem: str) -> int:
    # Every environments-v* bucket, so a uv bucket version bump keeps being counted
    buckets = _subdirs(cache_dir, ENVIRONMENTS_BUCKET_PREFIX)
    return sum(len(_subdirs(bucket, f"{stem}-")) for bucket in buckets)


class _Checked:
    done = False


def warn_if_many_script_envs(file_name: str, cache_dir: Path | None = None) -> None:
    # The parent process already checked before re-invoking
    if _Checked.done or bake_settings.bake_reinvoked:
        return
    _Checked.done = True
    limit = bake_settings.bake_script_env_warn_limit
    if limit == 0:
        return
    cache_dir = cache_dir or uv_cache_dir()
    if cache_dir is None:
        return
    stem = Path(file_name).stem
    count = count_script_envs(cache_dir, stem)
    if count < limit:
        return
    console.warning(
        f"uv has {count} {stem}-* script environments. Run {style.code('uv cache prune')} "
        f"to clear them ({style.code('BAKE_SCRIPT_ENV_WARN_LIMIT=0')} hides this)."
    )
