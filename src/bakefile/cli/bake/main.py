import typer
from typer.main import get_command_from_info

from bakefile.cli.bake.resolve_bakebook import resolve_bakebook
from bakefile.cli.utils.version import version_callback
from bakefile.exceptions import BakebookError

from .utils import get_bakebook_args

bake_app = typer.Typer(
    add_completion=False,
    # rich_markup_mode=None,  # ONLY for debugging
)

local_bake_app = typer.Typer(
    add_completion=False,
    # rich_markup_mode=None,  # ONLY for debugging
)


GET_BAKEBOOK = "get_bakebook"


# Common option definitions (reused across callbacks and commands)
chdir_option = typer.Option(None, "-C", "--chdir", help="Change directory before running")
file_name_option = typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py")
bakebook_name_option = typer.Option(
    "bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"
)
version_option = typer.Option(
    False,
    "--version",
    help="Show version and exit",
    callback=version_callback,
    is_eager=True,
)


def show_help_if_no_command(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@local_bake_app.callback(
    invoke_without_command=True,
)
def local_bake_app_callback(
    ctx: typer.Context,
    _chdir: str = chdir_option,
    _file_name: str = file_name_option,
    _bakebook_name: str = bakebook_name_option,
    _version: bool = version_option,
):
    show_help_if_no_command(ctx)


@bake_app.callback(
    invoke_without_command=True,
)
def bake_app_callback(
    ctx: typer.Context,
    _chdir: str = chdir_option,
    _file_name: str = file_name_option,
    _bakebook_name: str = bakebook_name_option,
    _version: bool = version_option,
):
    show_help_if_no_command(ctx)


@bake_app.command(
    name=GET_BAKEBOOK,
    hidden=True,
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    },
)
def get_bakebook(
    chdir: str = chdir_option,
    file_name: str = file_name_option,
    bakebook_name: str = bakebook_name_option,
):
    return resolve_bakebook(file_name=file_name, bakebook_name=bakebook_name, chdir=chdir)


def try_get_local_bake_app() -> typer.Typer | None:
    args = get_bakebook_args()

    for registered_command in bake_app.registered_commands:
        if registered_command.name == GET_BAKEBOOK:
            command = get_command_from_info(
                registered_command,
                pretty_exceptions_short=bake_app.pretty_exceptions_short,
                rich_markup_mode=bake_app.rich_markup_mode,
            )
            try:
                with command.make_context(info_name=GET_BAKEBOOK, args=args) as ctx:
                    bakebook = command.invoke(ctx)
                    local_bake_app.add_typer(bakebook)
                    return local_bake_app
            except BakebookError as e:
                typer.echo(str(e), err=True)
                return None


def main():
    local_bake_app = try_get_local_bake_app()
    if local_bake_app is None:
        bake_app()
    else:
        local_bake_app()
