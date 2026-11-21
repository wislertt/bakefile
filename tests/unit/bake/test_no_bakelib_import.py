import ast
from pathlib import Path

import pytest

import bake


def _imported_roots(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0:
        return [(node.module or "").split(".")[0]]
    return []


def _imports_bakelib(tree: ast.AST) -> bool:
    return any("bakelib" in _imported_roots(node) for node in ast.walk(tree))


def test_bake_does_not_import_bakelib() -> None:
    bake_dir = Path(bake.__file__).parent
    offenders = [
        str(path.relative_to(bake_dir))
        for path in sorted(bake_dir.rglob("*.py"))
        if _imports_bakelib(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert offenders == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import bakelib", True),
        ("import bakelib.space", True),
        ("from bakelib import Space", True),
        ("from bakelib.space.base import BaseSpace", True),
        ("from . import bakelib", False),
        ("import bake", False),
        ('LOG = "warning,bake=debug,bakelib=debug"', False),
    ],
)
def test_detects_bakelib_imports(source: str, expected: bool) -> None:
    assert _imports_bakelib(ast.parse(source)) is expected
