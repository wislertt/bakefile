import inspect

from bake import command
from bake.utils.constants import BAKE_COMMAND_KWARGS
from tests.bake.bakebook.utils import _assert_signature_matches_typer


def test_command_signature_matches_typer() -> None:
    _assert_signature_matches_typer(inspect.signature(command), "command", skip_self=True)


def test_command_marks_function() -> None:
    @command()
    def test_func():
        pass

    assert hasattr(test_func, BAKE_COMMAND_KWARGS)
    kwargs = object.__getattribute__(test_func, BAKE_COMMAND_KWARGS)
    assert kwargs["name"] is None
    assert kwargs["help"] is None


def test_command_with_parens() -> None:
    @command()
    def test_func():
        pass

    assert hasattr(test_func, BAKE_COMMAND_KWARGS)


def test_command_with_args() -> None:
    @command(name="custom-name", help="Custom help text")
    def test_func():
        pass

    assert hasattr(test_func, BAKE_COMMAND_KWARGS)
    # Custom values override defaults
    kwargs = object.__getattribute__(test_func, BAKE_COMMAND_KWARGS)
    assert kwargs["name"] == "custom-name"
    assert kwargs["help"] == "Custom help text"
