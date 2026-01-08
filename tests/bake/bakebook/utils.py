import inspect

import typer


def _assert_signature_matches_typer(
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
