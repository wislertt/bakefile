import os
import sys

import click


def get_bakebook_args(
    args: list[str] | None = None,
    windows_expand_args: bool = True,
) -> list[str]:
    # source from https://github.com/fastapi/typer/blob/b7f39eaad60141988f5d9a58df72c44d6128cd53/typer/core.py#L175-L185

    if args is None:
        args = sys.argv[1:]

        # Covered in Click tests
        if os.name == "nt" and windows_expand_args:  # pragma: no cover
            args = click.utils._expand_args(args)
    else:
        args = list(args)

    non_get_bakebook_args = ["--help", "--version"]

    args = [arg for arg in args if arg not in non_get_bakebook_args]
    return args
