import inspect

from bake import command
from tests.unit.bake.bakebook.utils import assert_signature_matches_typer


def test_command_signature_matches_typer() -> None:
    assert_signature_matches_typer(inspect.signature(command), "command", skip_self=True)
