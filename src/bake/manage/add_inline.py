import logging
import re
import sys
from pathlib import Path
from typing import Any

from bake.ui import console, run_uv
from bake.utils.exceptions import BakebookError

logger = logging.getLogger(__name__)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


def add_inline_metadata(bakefile_path: Path) -> None:
    if not bakefile_path.exists():
        logger.error(f"Bakefile not found at {bakefile_path}")
        raise BakebookError(
            f"Bakefile not found at {bakefile_path}. "
            f"Run 'bakefile init --inline' to create a new bakefile with PEP 723 metadata."
        )

    result = run_uv(
        ["init", "--script", str(bakefile_path.name)],
        check=False,
        cwd=bakefile_path.parent,
        echo=False,
    )

    is_already_pep723 = result.returncode == 2 and "is already a PEP 723 script" in result.stderr

    is_valid_output = result.returncode == 0 or is_already_pep723

    if not is_valid_output:
        command: str = " ".join(result.args)
        logger.error(f"Failed to initialize PEP 723 metadata for {bakefile_path}")
        raise BakebookError(
            f"Failed to initialize PEP 723 metadata.\n\n"
            f"Command: `{command}`\n\n"
            f"Error: {result.stderr.strip()}"
        )

    if is_already_pep723:
        console.warning(f"{bakefile_path.name} already has PEP 723 metadata")

    run_uv(
        ["add", "bakefile", "--script", str(bakefile_path.name)],
        cwd=bakefile_path.parent,
        echo=False,
    )


def read_inline(bakefile_path: Path) -> dict[str, Any] | None:
    inline_regex = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
    script = bakefile_path.read_text()
    name = "script"
    matches = list(filter(lambda m: m.group("type") == name, re.finditer(inline_regex, script)))

    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        content = "".join(
            line[2:] if line.startswith("# ") else line[1:]
            for line in matches[0].group("content").splitlines(keepends=True)
        )
        return tomllib.loads(content)
    else:
        return None
