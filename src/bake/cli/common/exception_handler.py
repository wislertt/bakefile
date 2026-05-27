import errno
import sys
from contextlib import contextmanager
from gettext import gettext
from typing import TextIO, cast

from typer._click import echo
from typer._click.exceptions import (
    Abort,
    ClickException,
    Exit,
)
from typer._click.utils import PacifyFlushWrapper
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
            echo(file=sys.stderr)
            raise Abort() from e
        except KeyboardInterrupt as e:
            raise Exit(130) from e
        except ClickException as e:
            if not standalone_mode:
                raise
            if HAS_RICH and rich_markup_mode is not None:
                import typer.rich_utils

                typer.rich_utils.rich_format_error(e)
            else:
                e.show()
            sys.exit(e.exit_code)
        except OSError as e:
            if e.errno == errno.EPIPE:
                sys.stdout = cast(TextIO, PacifyFlushWrapper(sys.stdout))
                sys.stderr = cast(TextIO, PacifyFlushWrapper(sys.stderr))
                sys.exit(1)
            raise
    except Exit as e:
        if standalone_mode:
            sys.exit(e.exit_code)
        else:
            # return exit code to caller
            raise
    except Abort:
        if not standalone_mode:
            raise
        if HAS_RICH and rich_markup_mode is not None:
            import typer.rich_utils

            typer.rich_utils.rich_abort_error()
        else:
            echo(gettext("Aborted!"), file=sys.stderr)
        sys.exit(1)
