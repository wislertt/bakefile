import sys
from dataclasses import dataclass
from typing import Annotated, Any

import click
import typer

from bake.bakebook.bakebook import Bakebook
from bake.cli.common.context import Context
from bake.ui import console
from bake.ui.run.main import run as _run

from .export import _format_shell_value, _get_data

KNOWN_OPTIONS = {"-s", "--secret"}


def _lookup_field(data: dict[str, Any], field_name: str) -> Any:
    lower_map = {k.lower(): k for k in data}
    lookup = field_name.lower()
    if lookup not in lower_map:
        available = ", ".join(sorted(data.keys()))
        raise typer.BadParameter(f"Field '{field_name}' not found. Available fields: {available}")
    return data[lower_map[lookup]]


@dataclass
class EnvInput:
    var_names: list[str]
    cmd: list[str] | None
    reveal_secrets: bool


def _parse_env_input(reveal_secrets: bool = False) -> EnvInput:
    try:
        env_idx = sys.argv.index("env")
    except ValueError:
        env_idx = -1

    has_double_dash = "--" in sys.argv

    if has_double_dash:
        dash_idx = sys.argv.index("--")
        cmd = sys.argv[dash_idx + 1 :]
        if not cmd:
            raise click.UsageError("No command specified after --.")
        raw_args = sys.argv[env_idx + 1 : dash_idx]
    else:
        cmd = None
        raw_args = sys.argv[env_idx + 1 :]

    var_names: list[str] = []
    for a in raw_args:
        if a.startswith("-"):
            if a not in KNOWN_OPTIONS:
                raise click.NoSuchOption(a, possibilities=list(KNOWN_OPTIONS))
        else:
            var_names.append(a)

    return EnvInput(var_names=var_names, cmd=cmd, reveal_secrets=reveal_secrets)


def _build_env_dict(bakebook: Bakebook, reveal_secrets: bool = False) -> dict[str, str]:
    data = _get_data(bakebook=bakebook, reveal_secrets=reveal_secrets)
    return {name.upper(): _format_shell_value(value) for name, value in data.items()}


def _build_selective_env_dict(
    bakebook: Bakebook, var_names: list[str], reveal_secrets: bool = False
) -> dict[str, str]:
    data = _get_data(bakebook=bakebook, reveal_secrets=reveal_secrets)
    return {name.upper(): _format_shell_value(_lookup_field(data, name)) for name in var_names}


def _env_print(bakebook: Bakebook, var_name: str, reveal_secrets: bool = False) -> None:
    data = _get_data(bakebook=bakebook, reveal_secrets=reveal_secrets)
    value = _lookup_field(data, var_name)
    console.plain_out.print(_format_shell_value(value), overflow="ignore", crop=False)


def _env(bakebook: Bakebook, env_input: EnvInput) -> None:
    if env_input.cmd is not None:
        env_dict = (
            _build_selective_env_dict(
                bakebook=bakebook,
                var_names=env_input.var_names,
                reveal_secrets=env_input.reveal_secrets,
            )
            if env_input.var_names
            else _build_env_dict(bakebook=bakebook, reveal_secrets=env_input.reveal_secrets)
        )
        try:
            result = _run(
                env_input.cmd, capture_output=False, check=False, env=env_dict, echo=False
            )
        except FileNotFoundError:
            console.error(f"Command not found: {env_input.cmd[0]}")
            raise typer.Exit(code=127) from None
        raise typer.Exit(code=result.returncode)
    elif not env_input.var_names:
        raise typer.Exit(code=0)
    elif len(env_input.var_names) > 1:
        raise click.BadArgumentUsage(
            "Only one variable name allowed without --. "
            "Use `bakefile env VAR1 VAR2 -- command` to inject multiple vars.",
        )
    else:
        _env_print(bakebook, env_input.var_names[0], reveal_secrets=env_input.reveal_secrets)


def env(
    ctx: Context,
    var_names: Annotated[
        str | None,
        typer.Argument(help="Variable name(s) to print or inject"),
    ] = None,
    secret: Annotated[
        bool,
        typer.Option(
            "--secret",
            "-s",
            help="Reveal SecretStr/SecretBytes values (default: masked)",
        ),
    ] = False,
) -> None:
    """Print variable values or inject them into a command.

    Use -- to separate variable names from the command to run.

    Examples:
        bakefile env NAME                    # Print a single value
        bakefile env NAME -s                 # Print a single value (reveal secrets)
        bakefile env -- command              # Inject all vars into command
        bakefile env NAME COUNT -- command   # Inject only specified vars
        bakefile env -s NAME -- command      # Inject with secrets revealed
    """
    _ = var_names
    env_input = _parse_env_input(reveal_secrets=secret)

    # Show help early (before get_bakebook — same pattern as run command)
    if not env_input.var_names and env_input.cmd is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=1)

    if ctx.obj.bakebook is None:
        ctx.obj.get_bakebook(allow_missing=False, reinvoke_cli_module="bake.cli.bakefile")

    if ctx.obj.bakebook is None:
        raise RuntimeError("Bakebook not found.")

    _env(bakebook=ctx.obj.bakebook, env_input=env_input)
