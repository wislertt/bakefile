import errno
import sys
from contextlib import contextmanager
from gettext import gettext
from typing import TextIO, cast

import click
from typer.core import HAS_RICH, MarkupMode


@contextmanager
def typer_exception_handler(
    *,
    standalone_mode: bool,
    rich_markup_mode: MarkupMode,
):
    # Reference code: https://github.com/fastapi/typer/blob/da9c4c67f3d8e4acd5f76e8909503bb999f1b751/typer/core.py#L186-L248
    try:
        try:
            yield
        except EOFError as e:
            click.echo(file=sys.stderr)
            raise click.Abort() from e
        except KeyboardInterrupt as e:
            raise click.exceptions.Exit(130) from e
        except click.ClickException as e:
            if not standalone_mode:
                raise
            if HAS_RICH and rich_markup_mode is not None:
                from typer import rich_utils

                rich_utils.rich_format_error(e)
            else:
                e.show()
            sys.exit(e.exit_code)
        except OSError as e:
            if e.errno == errno.EPIPE:
                sys.stdout = cast(TextIO, click.utils.PacifyFlushWrapper(sys.stdout))
                sys.stderr = cast(TextIO, click.utils.PacifyFlushWrapper(sys.stderr))
                sys.exit(1)
            raise
    except click.exceptions.Exit as e:
        if standalone_mode:
            sys.exit(e.exit_code)
        else:
            # return exit code to caller
            raise
    except click.Abort:
        if not standalone_mode:
            raise
        if HAS_RICH and rich_markup_mode is not None:
            from typer import rich_utils

            rich_utils.rich_abort_error()
        else:
            click.echo(gettext("Aborted!"), file=sys.stderr)
        sys.exit(1)
