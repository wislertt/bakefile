import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bake.manage.add_inline import add_inline_metadata, read_inline
from bake.ui.logger import strip_ansi
from bake.utils.constants import DEFAULT_FILE_NAME
from bake.utils.exceptions import BakebookError


def test_add_inline_to_existing_bakefile(empty_project_folder_no_inline: Path) -> None:
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME
    metadata = read_inline(bakefile_path)
    assert metadata is None

    add_inline_metadata(bakefile_path)

    dependencies = "dependencies"
    metadata = read_inline(bakefile_path)
    assert metadata is not None
    assert dependencies in metadata
    assert isinstance(metadata[dependencies], list)
    assert isinstance(metadata[dependencies][0], str)
    assert metadata[dependencies][0].startswith("bakefile[lib]>=")


def test_add_inline_raises_error_when_bakefile_not_found(tmp_path: Path) -> None:
    nonexistent_path = tmp_path / "nonexistent.py"

    with pytest.raises(BakebookError, match="Bakefile not found"):
        add_inline_metadata(nonexistent_path)


def test_add_inline_raises_error_when_uv_init_fails(
    empty_project_folder_no_inline: Path,
) -> None:
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

    failed_result = MagicMock()
    failed_result.returncode = 1
    failed_result.args = ["uv", "init", "--script", "bakefile.py"]
    failed_result.stderr = "Some initialization error"

    with (
        patch("bake.manage.add_inline.run_uv", return_value=failed_result),
        pytest.raises(BakebookError, match="Failed to initialize PEP 723 metadata"),
    ):
        add_inline_metadata(bakefile_path)


def test_add_inline_warns_when_already_pep723(
    empty_project_folder_no_inline: Path, capfd: pytest.CaptureFixture
) -> None:
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

    # Mock run_uv to simulate PEP 723 already exists (returncode 2 with specific message)
    init_result = MagicMock()
    init_result.returncode = 2
    init_result.stderr = "error: file `bakefile.py` is already a PEP 723 script"

    add_result = MagicMock()

    def mock_run_uv(args, **_):
        if "init" in args:
            return init_result
        return add_result

    with patch("bake.manage.add_inline.run_uv", side_effect=mock_run_uv):
        add_inline_metadata(bakefile_path)

    captured = capfd.readouterr()
    assert "already has PEP 723 metadata" in strip_ansi(captured.err)


def test_read_inline_raises_error_on_multiple_script_blocks(tmp_path: Path) -> None:
    bakefile_path = tmp_path / "test.py"
    bakefile_path.write_text(
        textwrap.dedent(
            """\
            # /// script
            # dependencies = []
            # ///

            # /// script
            # dependencies = []
            # ///
            """
        )
    )

    with pytest.raises(ValueError, match="Multiple script blocks found"):
        read_inline(bakefile_path)


def test_read_inline_returns_none_when_no_script_block(tmp_path: Path) -> None:
    bakefile_path = tmp_path / "test.py"
    bakefile_path.write_text("# Just a comment\n")

    result = read_inline(bakefile_path)
    assert result is None


def test_read_inline_parses_single_script_block(tmp_path: Path) -> None:
    bakefile_path = tmp_path / "test.py"
    bakefile_path.write_text(
        textwrap.dedent(
            """\
            # /// script
            # dependencies = ["bakefile"]
            # ///
            """
        )
    )

    result = read_inline(bakefile_path)
    assert result is not None
    assert "dependencies" in result
    assert result["dependencies"] == ["bakefile"]
