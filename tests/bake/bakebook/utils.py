import inspect
import types
from dataclasses import dataclass

import typer

from bake import Bakebook


def assert_signature_matches_typer(
    func_sig: inspect.Signature,
    func_name: str,
    *,
    skip_self: bool = False,
) -> None:
    """Assert that a signature matches Typer's Typer.command()."""
    typer_command_sig = inspect.signature(typer.Typer.command)
    typer_params = [p for p in typer_command_sig.parameters if not (skip_self and p == "self")]
    func_params = list(func_sig.parameters.keys())

    assert func_params == typer_params, (
        f"Signature mismatch for {func_name}:\n"
        f"  {func_name} params: {func_params}\n"
        f"  typer params: {typer_params}"
    )

    for param_name in func_params:
        func_param = func_sig.parameters[param_name]
        typer_param = typer_command_sig.parameters[param_name]
        func_default = getattr(func_param.default, "value", func_param.default)
        typer_default = getattr(typer_param.default, "value", typer_param.default)
        assert func_default == typer_default


@dataclass
class ExpectedCommand:
    """Expected command for assertion in tests."""

    name: str
    command_type: type[types.FunctionType | types.MethodType]
    output: str | None = None


def assert_commands(
    bakebook: Bakebook,
    expected_commands: dict[str, ExpectedCommand],
    msg: str = "",
) -> None:
    """Assert that registered commands match expected names and results."""
    registered = bakebook._app.registered_commands
    assert len(registered) == len(expected_commands), (
        f"{msg}: Expected {len(expected_commands)} commands, got {len(registered)}"
    )

    for cmd_info in registered:
        callback = cmd_info.callback
        assert isinstance(callback, (types.MethodType, types.FunctionType))
        callback_name = callback.__name__
        assert callback_name in expected_commands, f"{msg}: Unexpected callback {callback_name}"
        expected = expected_commands[callback_name]
        assert isinstance(callback, expected.command_type), (
            f"{msg}: {callback_name} expected type {expected.command_type}, got {type(callback)}"
        )
        if expected.output is not None:
            result = callback()
            assert result == expected.output, (
                f"{msg}: {callback_name}() returned {result!r}, expected {expected.output!r}"
            )
