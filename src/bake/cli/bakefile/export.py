import shlex
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import orjson
import typer
import yaml
from pydantic import SecretBytes, SecretStr
from pydantic.fields import FieldInfo

from bake._typer_compat import BadParameter
from bake.bakebook.bakebook import Bakebook
from bake.cli.common.context import Context
from bake.ui import console
from bake.utils.unwrap import unwrap

ExportFormat = Literal["sh", "dotenv", "json", "yaml"]
JsonValue = str | float | bool | None | list[Any] | dict[Hashable, Any]


def _format_shell_value(value: JsonValue) -> str:
    """Format a value for shell export.

    Expects JSON-serializable types (str, int, float, bool, None, list, dict).
    Raises TypeError for unexpected types.

    SecretStr values are masked for security.

    Parameters
    ----------
    value : Any
        The value to format for shell export

    Returns
    -------
    str
        Shell-formatted string ready for export

    Raises
    ------
    TypeError
        If value is not one of the expected types
    """

    if isinstance(value, (list, dict)):
        # Complex types: JSON string, then shell-quote it
        return shlex.quote(orjson.dumps(value).decode())
    elif isinstance(value, str):
        # Strings: shell-quote directly
        return shlex.quote(value)
    elif value is None:
        # None becomes empty string
        return ""
    elif isinstance(value, bool):
        # Booleans: lowercase true/false for shell compatibility
        return str(value).lower()
    elif isinstance(value, (int, float)):
        # Numbers: convert to string, no quoting needed
        return str(value)
    raise TypeError(
        f"Unexpected type for shell export: {type(value).__name__}. "
        f"Expected one of: str, int, float, bool, None, list, dict"
    )


def _format_dotenv_value(value: JsonValue) -> str:
    """Format a value for dotenv export.

    Uses smart quote selection to produce valid dotenv format that
    python-dotenv's parser can handle.

    Parameters
    ----------
    value : JsonValue
        The value to format for dotenv export

    Returns
    -------
    str
        Dotenv-formatted string ready for export

    Raises
    ------
    TypeError
        If value is not one of the expected types
    """
    if isinstance(value, (list, dict)):
        # Complex types: JSON string, then wrap in double quotes
        json_str = orjson.dumps(value).decode()
        return '"' + json_str.replace("\\", "\\\\").replace('"', '\\"') + '"'
    elif isinstance(value, str):
        # Strings: use smart quote selection
        if value.isalnum():
            return value
        if "'" in value and '"' not in value:
            # Has single quotes only: use double quotes
            return f'"{value}"'
        if '"' in value and "'" not in value:
            # Has double quotes only: use single quotes
            return f"'{value}'"
        # Has both or special chars: use double quotes with escaping
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    elif value is None:
        return ""
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    raise TypeError(
        f"Unexpected type for dotenv export: {type(value).__name__}. "
        f"Expected one of: str, int, float, bool, None, list, dict"
    )


def _filter_data(data: dict[str, Any], include: list[str]) -> dict[str, Any]:
    lower_map = {k.lower(): k for k in data}
    unknown = [i for i in include if i.lower() not in lower_map]
    if unknown:
        raise BadParameter(f"Unknown keys: {', '.join(sorted(unknown))}")
    return {k: data[lower_map[k.lower()]] for k in include}


def _format_vars(data: dict, value_formatter: Callable[[JsonValue], str], prefix: str = "") -> str:
    lines: list[str] = []
    for field_name, value in data.items():
        formatted_val = value_formatter(value)
        lines.append(f"{prefix}{field_name.upper()}={formatted_val}")
    return "\n".join(lines)


class ExportFormatter:
    def __call__(self, data: dict[str, Any]) -> str:
        raise NotImplementedError("....")


class ShExportFormatter(ExportFormatter):
    def __call__(self, data: dict[str, Any]) -> str:
        return _format_vars(data, value_formatter=_format_shell_value, prefix="export ")


class DotEnvExportFormatter(ExportFormatter):
    def __call__(self, data: dict[str, Any]) -> str:
        return _format_vars(data, value_formatter=_format_dotenv_value, prefix="")


class JsonExportFormatter(ExportFormatter):
    def __call__(self, data: dict[str, Any]) -> str:
        return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()


class YamlExportFormatter(ExportFormatter):
    def __call__(self, data: dict[str, Any]) -> str:
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


def _reveal_secrets(bakebook: Bakebook, data: dict[str, Any]) -> dict[str, Any]:
    for field_name in cast(dict[str, FieldInfo], bakebook.__class__.model_fields):
        value = getattr(bakebook, field_name, None)
        if isinstance(value, (SecretStr, SecretBytes)):
            secret_val = cast(SecretStr | SecretBytes, value).get_secret_value()
            data[field_name] = secret_val.decode() if isinstance(secret_val, bytes) else secret_val
    return data


def _get_data(bakebook: Bakebook, reveal_secrets: bool = False) -> dict[str, Any]:
    data = cast(dict[str, Any], bakebook.model_dump(mode="json"))
    if reveal_secrets:
        data = _reveal_secrets(bakebook=bakebook, data=data)
    return data


def _export(
    bakebook: Bakebook,
    format: ExportFormat = "sh",
    output: Path | None = None,
    include: list[str] | None = None,
    reveal_secrets: bool = False,
) -> None:
    formatters: dict[str, ExportFormatter] = {
        "sh": ShExportFormatter(),
        "dotenv": DotEnvExportFormatter(),
        "json": JsonExportFormatter(),
        "yaml": YamlExportFormatter(),
    }

    formatter = formatters.get(format)
    if formatter is None:
        raise ValueError(f"Unknown format: {format}")

    data = _get_data(bakebook=bakebook, reveal_secrets=reveal_secrets)

    if include is not None:
        data = _filter_data(data=data, include=include)

    content = formatter(data)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    elif content != "":
        console.echo(content, no_color=True, overflow="ignore", crop=False)


def export(
    ctx: Context,
    format: Annotated[
        ExportFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
        ),
    ] = "sh",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: stdout)",
            exists=False,
        ),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--include",
            "-i",
            help="Keys to export (default: all)",
        ),
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
    """Export bakebook args to external formats.

    Export Pydantic-validated bakebook args to various formats for use
    outside Python runtime (shell scripts, GitHub Actions, .env files, etc.).

    Examples:
        # Export to shell for eval
        bakefile export --format sh

        # Export to dotenv file
        bakefile export --format dotenv --output .env

        # Export to JSON
        bakefile export --format json --output config.json

        # Export specific keys only
        bakefile export --include database_url --include api_key
    """
    if ctx.obj.bakebook is None:
        ctx.obj.get_bakebook(allow_missing=False, reinvoke_cli_module="bake.cli.bakefile")

    _export(
        bakebook=unwrap(ctx.obj.bakebook),
        format=format,
        output=output,
        include=include,
        reveal_secrets=secret,
    )
