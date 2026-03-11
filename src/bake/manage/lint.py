import logging
import subprocess
from pathlib import Path

from ruff.__main__ import find_ruff_bin
from ty.__main__ import find_ty_bin

from bake.ui.run import run

logger = logging.getLogger(__name__)


def run_ruff(
    bakefile_path: Path,
    subcommand: str,
    args: list[str],
    *,
    only_bakefile: bool = False,
    check: bool = True,
    dry_run: bool = False,
    echo: bool = True,
) -> subprocess.CompletedProcess[str]:
    ruff_bin = find_ruff_bin()
    target = bakefile_path.name if only_bakefile else "."
    cmd = [subcommand, *args, target]
    return run(
        [str(ruff_bin), *cmd],
        cwd=bakefile_path.parent,
        capture_output=True,
        stream=True,
        check=check,
        echo=echo,
        echo_cmd="ruff " + " ".join(cmd) if echo else None,
        dry_run=dry_run,
    )


def run_ruff_format(
    bakefile_path: Path,
    *,
    only_bakefile: bool = False,
    check: bool = True,
    dry_run: bool = False,
    echo: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run_ruff(
        bakefile_path=bakefile_path,
        subcommand="format",
        args=["--exit-non-zero-on-format"],
        only_bakefile=only_bakefile,
        check=check,
        dry_run=dry_run,
        echo=echo,
    )


def run_ruff_check(
    bakefile_path: Path,
    *,
    only_bakefile: bool = False,
    line_length: int = 100,
    check: bool = True,
    dry_run: bool = False,
    echo: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run_ruff(
        bakefile_path=bakefile_path,
        subcommand="check",
        args=[
            "--fix",
            "--exit-non-zero-on-fix",
            "--extend-select",
            "ARG,B,C4,E,F,I,N,PGH,PIE,PYI,RUF,SIM,UP",
            "--line-length",
            str(line_length),
        ],
        only_bakefile=only_bakefile,
        check=check,
        dry_run=dry_run,
        echo=echo,
    )


def run_ty_check(
    bakefile_path: Path,
    python_path: Path,
    *,
    only_bakefile: bool = False,
    check: bool = True,
    dry_run: bool = False,
    echo: bool = True,
) -> subprocess.CompletedProcess[str]:
    ty_bin = find_ty_bin()
    cmd = ["check", "--error-on-warning", "--no-progress", "--python", str(python_path)]
    if only_bakefile:
        cmd.append(bakefile_path.name)

    return run(
        [str(ty_bin), *cmd],
        cwd=bakefile_path.parent,
        capture_output=True,
        stream=True,
        check=check,
        echo=echo,
        echo_cmd="ty " + " ".join(cmd) if echo else None,
        dry_run=dry_run,
    )
