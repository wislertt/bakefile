import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]

# Runs against the wheel only: it goes first on sys.path, ahead of the editable install
RESOLVE_TEMPLATES = textwrap.dedent(
    """
    import sys
    import bakelib
    import bakelib.space

    assert bakelib.__file__.startswith(sys.argv[1]), bakelib.__file__
    from bakelib.space.base import BaseSpace

    for name in bakelib.space.__all__:
        space_cls = getattr(bakelib.space, name)
        if isinstance(space_cls, type) and issubclass(space_cls, BaseSpace):
            for path, managed_file in space_cls.__new__(space_cls)._get_managed_files().items():
                assert managed_file.read_template(), path
                print(path)
    """
)


def test_every_declared_template_resolves_from_the_built_wheel(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)], cwd=REPO_ROOT, check=True
    )
    (wheel,) = tmp_path.glob("bakefile-*.whl")

    result = subprocess.run(
        [sys.executable, "-c", RESOLVE_TEMPLATES, str(wheel)],
        cwd=tmp_path,
        # Windows needs SYSTEMROOT and friends to import asyncio, so extend the env, not replace it
        env={**os.environ, "PYTHONPATH": str(wheel)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "oxfmt.config.ts" in result.stdout.splitlines()
