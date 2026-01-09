import inspect

from bake import command
from tests.bake.bakebook.utils import _assert_signature_matches_typer


def test_command_signature_matches_typer() -> None:
    _assert_signature_matches_typer(inspect.signature(command), "command", skip_self=True)
