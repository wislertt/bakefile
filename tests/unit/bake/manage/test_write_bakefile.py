import types
from pathlib import Path

import pytest

from bake.manage.write_bakefile import write_bakefile
from bake.samples import simple
from bake.utils.constants import (
    BAKEBOOK_NAME_IN_SAMPLES,
    DEFAULT_FILE_NAME,
)


def test_write_bakefile(tmp_path: Path) -> None:
    bakebook_name = "my_bakebook"
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    write_bakefile(
        bakefile_path=bakefile_path,
        bakebook_name=bakebook_name,
        sample_module=simple,
    )

    assert bakefile_path.exists()

    content = bakefile_path.read_text()
    assert bakebook_name in content
    assert BAKEBOOK_NAME_IN_SAMPLES not in content


def test_write_bakefile_module_missing_bakebook_attribute(tmp_path: Path) -> None:
    module = types.ModuleType("fake_module")
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    with pytest.raises(ValueError, match="must have `__bakebook__` attribute"):
        write_bakefile(
            bakefile_path=bakefile_path,
            bakebook_name="my_bakebook",
            sample_module=module,
        )


def test_write_bakefile_module_missing_file_attribute(tmp_path: Path) -> None:
    class FakeModule(types.ModuleType):
        __file__ = None
        __bakebook__ = "some_bakebook"

    fake_module = FakeModule("fake_module")
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    with pytest.raises(ValueError, match="Could not find `fake_module`"):
        write_bakefile(
            bakefile_path=bakefile_path,
            bakebook_name="my_bakebook",
            sample_module=fake_module,
        )
