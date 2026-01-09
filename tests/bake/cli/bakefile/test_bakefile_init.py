from pathlib import Path

import pytest

from bake.utils.constants import (
    CMD_BAKEFILE,
    CMD_INIT,
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_FILE_NAME,
)
from tests.conftest import RunCli


@pytest.mark.integration
@pytest.mark.parametrize(
    "extra_args,expected_file,expected_content",
    [
        ([], DEFAULT_FILE_NAME, DEFAULT_BAKEBOOK_NAME),
        (["-b", "my_tasks"], DEFAULT_FILE_NAME, "my_tasks"),
        (["-f", "MyBakefile.py"], "MyBakefile.py", DEFAULT_BAKEBOOK_NAME),
    ],
)
def test_init_creates_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
    extra_args: list[str],
    expected_file: str,
    expected_content: str,
) -> None:
    captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[*extra_args, CMD_INIT])

    assert captured.exit_code == 0
    assert "Successfully created bakefile" in captured.out

    bakefile = tmp_path / expected_file
    assert bakefile.exists()

    content = bakefile.read_text()
    assert expected_content in content


@pytest.mark.integration
def test_init_fails_if_file_exists_without_force(tmp_path: Path, run_cli: RunCli) -> None:
    bakefile = tmp_path / DEFAULT_FILE_NAME
    bakefile.write_text("# existing content")

    captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_INIT])

    assert captured.exit_code == 1
    assert "ERROR" in captured.err
    assert "File already exists" in captured.err
    assert "--force" in captured.err

    # File should not be overwritten
    assert bakefile.read_text() == "# existing content"


@pytest.mark.integration
def test_init_overwrites_with_force(tmp_path: Path, run_cli: RunCli) -> None:
    bakefile = tmp_path / DEFAULT_FILE_NAME
    bakefile.write_text("# old content")

    captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_INIT, "--force"])

    assert captured.exit_code == 0

    content = bakefile.read_text()
    assert "# old content" not in content
    assert DEFAULT_BAKEBOOK_NAME in content
