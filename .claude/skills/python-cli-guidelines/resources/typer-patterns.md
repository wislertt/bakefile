# Typer Patterns

Common patterns for building CLI tools with Typer.

## Basic Command

```python
import typer

app = typer.Typer(help="bakefile - Python build system")

@app.command()
def test():
    """Run tests for the project."""
    typer.echo("Running tests...")

if __name__ == "__main__":
    app()
```

## Command with Arguments

```python
@app.command()
def run(
    task: str = typer.Argument(..., help="Task name to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Run a specific task."""
    if verbose:
        typer.echo(f"Running task: {task}")
```

## Subcommands

```python
# Main app
app = typer.Typer()

# Subcommand groups
bakefile_app = typer.Typer()
app.add_typer(bakefile_app, name="bakefile")

@bakefile_app.command()
def init():
    """Initialize bakefile in current directory."""
    pass

@bakefile_app.command()
def lint():
    """Lint and format bakefile code."""
    pass
```

## Callback for Global Options

```python
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    config: str = typer.Option("bakefile.py", "--config", "-c")
):
    """Global options available to all commands."""
    pass
```

## Exit Codes

```python
import sys

@app.command()
def build():
    """Build the project."""
    success = do_build()
    raise typer.Exit(code=0 if success else 1)
```

## Rich Output (for styled output)

```python
from rich.console import Console
from rich.panel import Panel

console = Console()

@app.command()
def status():
    """Show project status."""
    console.print(Panel("Status: OK", style="green"))
```

## Environment Variables

```python
@app.command()
def run(
    env: str = typer.Option(
        "dev",
        "--env",
        envvar="BAKEFILE_ENV"
    )
):
    """Run with environment variable support."""
    pass
```

## Confirmation Prompts

```python
@app.command()
def clean():
    """Clean build artifacts."""
    if typer.confirm("Delete all build artifacts?"):
        typer.echo("Cleaning...")
```

## Progress Bars

```python
from rich.progress import track

@app.command()
def install():
    """Install dependencies."""
    for item in track(items, description="Installing"):
        process(item)
```

## File Path Arguments

```python
from pathlib import Path

@app.command()
def validate(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True
    )
):
    """Validate a bakefile.py."""
    pass
```

## Best Practices

1. **Use type hints** - Typer uses them for option types
2. **Provide help text** - All commands/options should have `help=`
3. **Validate inputs** - Use Pydantic for complex validation
4. **Return exit codes** - Use `typer.Exit()` for proper codes
5. **Group related commands** - Use subapps for organization
