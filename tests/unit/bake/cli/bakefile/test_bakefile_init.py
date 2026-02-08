from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from bake import Bakebook
from bake.utils.constants import (
    CMD_BAKEFILE,
    CMD_INIT,
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_FILE_NAME,
)
from bake.utils.exceptions import BakebookError
from tests.conftest import RunCli
from tests.utils.cli import get_error_label


@pytest.mark.parametrize(
    "extra_args,init_args,expected_file,expected_content,expected_success_message",
    [
        (
            [],
            [],
            DEFAULT_FILE_NAME,
            DEFAULT_BAKEBOOK_NAME,
            "Successfully created bakefile",
        ),
        (["-b", "my_tasks"], [], DEFAULT_FILE_NAME, "my_tasks", "Successfully created bakefile"),
        (
            ["-f", "MyBakefile.py"],
            [],
            "MyBakefile.py",
            DEFAULT_BAKEBOOK_NAME,
            "Successfully created bakefile",
        ),
        (
            [],
            ["--inline"],
            DEFAULT_FILE_NAME,
            DEFAULT_BAKEBOOK_NAME,
            "Successfully created bakefile with PEP 723 metadata",
        ),
    ],
)
def test_init_creates_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
    extra_args: list[str],
    init_args: list[str],
    expected_file: str,
    expected_content: str,
    expected_success_message: str,
) -> None:
    captured = run_cli(
        command=CMD_BAKEFILE, dir_path=tmp_path, args=[*extra_args, CMD_INIT, *init_args]
    )

    assert captured.exit_code == 0
    assert expected_success_message in captured.out

    bakefile = tmp_path / expected_file
    assert bakefile.exists()

    content = bakefile.read_text()
    assert expected_content in content


def test_init_fails_if_file_exists_without_force(tmp_path: Path, run_cli: RunCli) -> None:
    bakefile = tmp_path / DEFAULT_FILE_NAME
    bakefile.write_text("# existing content")

    captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_INIT])

    assert captured.exit_code == 1
    assert get_error_label() in captured.err
    assert "File already exists" in captured.err
    assert "--force" in captured.err

    # File should not be overwritten
    assert bakefile.read_text() == "# existing content"


def test_init_overwrites_with_force(tmp_path: Path, run_cli: RunCli) -> None:
    bakefile = tmp_path / DEFAULT_FILE_NAME
    bakefile.write_text("# old content")

    captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_INIT, "--force"])

    assert captured.exit_code == 0

    content = bakefile.read_text()
    assert "# old content" not in content
    assert DEFAULT_BAKEBOOK_NAME in content


def test_init_with_inline_fails_when_add_metadata_raises_error(
    tmp_path: Path, run_cli: RunCli
) -> None:
    """Test that init --inline fails when add_inline_metadata raises BakebookError."""

    def mock_add_inline(*_, **__):
        raise BakebookError("Failed to initialize PEP 723 metadata")

    with patch("bake.cli.bakefile.init.add_inline_metadata", side_effect=mock_add_inline):
        captured = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_INIT, "--inline"])

    assert captured.exit_code == 1
    assert "Failed to add PEP 723 metadata" in captured.err


def test_init_fails_when_bakebook_already_loaded_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Test that init fails when bakebook is already loaded and --force is not used.

    This test mocks the scenario where ctx.obj.bakebook is already set
    (simulating a loaded bakebook from a previous command or context).
    """
    from bake.cli.bakefile.init import init

    # Create a mock context with a pre-loaded bakebook
    mock_ctx = MagicMock()
    mock_ctx.obj.bakebook = Bakebook()
    mock_ctx.obj.bakefile_path = tmp_path / DEFAULT_FILE_NAME
    mock_ctx.obj.chdir = tmp_path
    mock_ctx.obj.file_name = DEFAULT_FILE_NAME
    mock_ctx.obj.bakebook_name = DEFAULT_BAKEBOOK_NAME
    mock_ctx.obj.dry_run = True

    # This should raise typer.Exit with exit code 1
    with pytest.raises(typer.Exit) as exc_info:
        init(ctx=mock_ctx, force=False)

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Bakebook already loaded" in captured.err
