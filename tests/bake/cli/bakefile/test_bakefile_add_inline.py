from pathlib import Path

from bake.manage.add_inline import read_inline
from bake.utils.constants import CMD_ADD_INLINE, CMD_BAKEFILE, DEFAULT_FILE_NAME
from tests.conftest import RunCli


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
    assert "ERROR" in result.err
    assert "Bakefile not found at" in result.err
    assert "Run `bakefile init --inline` to" in result.err
