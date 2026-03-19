import inspect
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

_UNWRAP_ERROR_MESSAGE = "called `unwrap()` on a `None` value"


def unwrap(value: T | None) -> T:
    if value is None:
        # Try to get variable name from caller's source code
        frame = inspect.currentframe()
        if not frame:
            raise ValueError(_UNWRAP_ERROR_MESSAGE)  # pragma: no cover

        caller = frame.f_back
        if not caller:
            raise ValueError(_UNWRAP_ERROR_MESSAGE)  # pragma: no cover

        info = inspect.getframeinfo(caller)
        path = Path(info.filename).resolve()
        try:
            rel_path = path.relative_to(Path.cwd().resolve())
            path: Path = rel_path
        except ValueError:
            pass
        raise ValueError(f"{_UNWRAP_ERROR_MESSAGE}, {path}:{info.lineno}")
    return value
