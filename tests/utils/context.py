from pathlib import Path

import click
import pytest

from bake import Context
from bake.cli.common.obj import BakefileObject


class SimpleTestCommand(click.Command):
    """Minimal click.Command for testing Context."""

    def __init__(self):
        super().__init__(
            name="test",
            callback=lambda: None,
        )


@pytest.fixture
def mock_ctx(tmp_path: Path):
    obj = BakefileObject(
        chdir=tmp_path,
        file_name="bakefile.py",
        bakebook_name="bakebook",
        dry_run=True,
        verbosity=0,
    )

    command = SimpleTestCommand()
    ctx = Context(command=command, obj=obj, info_name="test")

    return ctx
