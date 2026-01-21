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


def test_write_bakefile_module_not_in_allowed_list(tmp_path: Path) -> None:
    module = types.ModuleType("fake_module")
    setattr(module, BAKEBOOK_NAME_IN_SAMPLES, "fake_bakebook")
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    with pytest.raises(ValueError, match="is not in the allowed sample modules list"):
        write_bakefile(
            bakefile_path=bakefile_path,
            bakebook_name="my_bakebook",
            sample_module=module,
        )


def test_write_bakefile_module_object_mismatch(tmp_path: Path) -> None:
    module = types.ModuleType(simple.__name__)
    setattr(module, BAKEBOOK_NAME_IN_SAMPLES, "fake_bakebook")
    module.__file__ = simple.__file__
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    with pytest.raises(ValueError, match="does not match the allowed module object"):
        write_bakefile(
            bakefile_path=bakefile_path,
            bakebook_name="my_bakebook",
            sample_module=module,
        )


def test_write_bakefile_module_file_is_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bake.manage.write_bakefile import ALLOWED_SAMPLE_MODULES

    module = types.ModuleType(simple.__name__)
    setattr(module, BAKEBOOK_NAME_IN_SAMPLES, "fake_bakebook")
    module.__file__ = None
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    monkeypatch.setitem(ALLOWED_SAMPLE_MODULES, simple.__name__, module)

    with pytest.raises(ValueError, match="Could not find file for module"):
        write_bakefile(
            bakefile_path=bakefile_path,
            bakebook_name="my_bakebook",
            sample_module=module,
        )
