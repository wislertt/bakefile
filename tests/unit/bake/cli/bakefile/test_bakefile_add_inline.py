from pathlib import Path
from unittest.mock import patch

from bake.manage.add_inline import read_inline
from bake.utils.constants import CMD_ADD_INLINE, CMD_BAKEFILE, DEFAULT_FILE_NAME
from bake.utils.exceptions import BakebookError
from tests.conftest import RunCli
from tests.utils.cli import get_error_label
from tests.utils.misc import remove_whitespace


def test_add_inline_cli(
    empty_project_folder_no_inline: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

    metadata = read_inline(bakefile_path)
    assert metadata is None

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder_no_inline, args=[CMD_ADD_INLINE]
    )

    assert result.exit_code == 0
    assert "Successfully added PEP 723 inline metadata" in result.out

    metadata = read_inline(bakefile_path)
    assert metadata is not None
    dependencies = "dependencies"
    assert dependencies in metadata
    assert isinstance(metadata[dependencies], list)
    assert isinstance(metadata[dependencies][0], str)
    assert metadata[dependencies][0].startswith("bakefile>=")


def test_add_inline_cli_nonexistent_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["add-inline"])

    assert result.exit_code == 1
    result_err = result.err.replace("\n", "")

    assert get_error_label() in result_err
    assert "Bakefile not found at" in result_err

    assert remove_whitespace("Run `bakefile init --inline` to") in remove_whitespace(result_err)


def test_add_inline_cli_handles_metadata_error(
    empty_project_folder_no_inline: Path,
    run_cli: RunCli,
) -> None:
    """Test that add_inline handles BakebookError from add_inline_metadata."""

    def mock_add_inline_metadata(*_, **__):
        raise BakebookError("Failed to add PEP 723 metadata")

    with patch(
        "bake.cli.bakefile.add_inline.add_inline_metadata",
        side_effect=mock_add_inline_metadata,
    ):
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=empty_project_folder_no_inline,
            args=[CMD_ADD_INLINE],
        )

    assert result.exit_code == 1
    assert "Failed to add PEP 723 metadata" in result.err
