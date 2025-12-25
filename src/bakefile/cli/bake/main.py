import typer
from typer.main import get_command_from_info

from bakefile.cli.bake.resolve_bakebook import resolve_bakebook

app = typer.Typer(
    add_completion=True,
    # rich_markup_mode=None,  # ONLY for debugging
)


# bakebook_1 = resolve_bakebook(file_name="bakefile.py", bakebook_name="bakebook", chdir=None)
# app.add_typer(bakebook_1, name="bakebook")


@app.command(
    name="bake", context_settings={"allow_extra_args": True, "allow_interspersed_args": False}
)
def bake(
    # ctx: typer.Context,
    chdir: str = typer.Option(None, "-C", "--chdir", help="Change directory before running"),
    file_name: str = typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py"),
    bakebook_name: str = typer.Option(
        "bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"
    ),
    # version: bool = typer.Option(
    #     False,
    #     "--version",
    #     help="Show version and exit",
    #     callback=version_callback,
    #     is_eager=True,
    # ),
):
    # _ = version
    print("start bake")
    bakebook = resolve_bakebook(file_name=file_name, bakebook_name=bakebook_name, chdir=chdir)

    print("get bakebook")
    return bakebook


def main():
    for registered_command in app.registered_commands:
        if registered_command.name == "bake":
            command = get_command_from_info(
                registered_command,
                pretty_exceptions_short=app.pretty_exceptions_short,
                rich_markup_mode=app.rich_markup_mode,
            )
            with command.make_context("bake", []) as ctx:
                bakebook = command.invoke(ctx)
                print(type(bakebook))

                app.add_typer(bakebook)

                app()
