import shlex
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import Annotated, Any, Literal

import orjson
import typer
import yaml
from pydantic_settings import BaseSettings

from bake.cli.common.context import Context
from bake.ui import console

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


def _export(
    bakebook: BaseSettings,
    format: ExportFormat = "sh",
    output: Path | None = None,
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

    data: dict[str, Any] = bakebook.model_dump(mode="json")
    content = formatter(data)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    elif content != "":
        console.echo(content, overflow="ignore", crop=False)


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
    """
    if ctx.obj.bakebook is None:
        ctx.obj.get_bakebook(allow_missing=False)

    if ctx.obj.bakebook is None:
        raise RuntimeError("Bakebook not found.")

    _export(bakebook=ctx.obj.bakebook, format=format, output=output)
