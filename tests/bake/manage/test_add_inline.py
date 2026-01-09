from pathlib import Path

from bake.manage.add_inline import add_inline_metadata, read_inline
from bake.utils.constants import DEFAULT_FILE_NAME


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
    assert metadata[dependencies][0].startswith("bakefile>=")
