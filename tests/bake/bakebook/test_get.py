from pathlib import Path
from unittest.mock import patch

import pytest

from bake import Bakebook
from bake.bakebook.get import (
    get_bakebook_from_module,
    get_bakebook_from_target_dir_path,
    get_target_dir_path,
    load_module,
    resolve_bakefile_path,
    validate_bakebook,
)
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from bake.utils.exceptions import BakebookError


class TestGetTargetDirPath:
    def test_get_target_dir_path_valid(self, tmp_path: Path) -> None:
        result = get_target_dir_path(chdir=tmp_path, create_if_not_exist=False)
        assert result == tmp_path.resolve()

    def test_get_target_dir_path_with_create(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "new" / "nested" / "dir"
        result = get_target_dir_path(new_dir, create_if_not_exist=True)

        assert new_dir.exists()
        assert result == new_dir.resolve()

    @pytest.mark.parametrize(
        "chdir",
        [Path("/nonexistent/path/12345")],
    )
    def test_get_target_dir_path_invalid_path(self, chdir: Path) -> None:
        with pytest.raises(BakebookError):
            get_target_dir_path(chdir=chdir, create_if_not_exist=False)

    def test_get_target_dir_path_not_a_directory(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(BakebookError):
            get_target_dir_path(chdir=file_path, create_if_not_exist=False)


class TestResolveBakefilePath:
    def test_resolve_bakefile_path_valid(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.py"
        file_path.write_text("print('test')")

        result = resolve_bakefile_path(tmp_path, "test.py")
        assert result == file_path.resolve()

    def test_resolve_bakefile_path_not_found(self, tmp_path: Path) -> None:
        file_name = "nonexistent.py"
        bakefile_path = resolve_bakefile_path(tmp_path, file_name)
        assert bakefile_path == tmp_path / file_name


class TestLoadModule:
    def test_load_module_valid(self, tmp_path: Path) -> None:
        module_path = tmp_path / "test_module.py"
        module_path.write_text("value = 42")

        module = load_module(module_path)
        assert hasattr(module, "value")
        assert module.value == 42

    def test_load_module_none_spec(self) -> None:
        with patch(
            "bake.bakebook.get.importlib.util.spec_from_file_location",
            return_value=None,
        ):
            fake_path = Path("fake.py")
            with pytest.raises(BakebookError):
                load_module(fake_path)


class TestValidateBakebook:
    def test_validate_bakebook_valid(self) -> None:
        bakebook = Bakebook()
        result = validate_bakebook(bakebook, "test")
        assert result is bakebook

    def test_validate_bakebook_invalid_type(self) -> None:
        with pytest.raises(BakebookError):
            validate_bakebook("not_a_typer", "test")


class TestGetBakebookFromModule:
    def test_get_bakebook_from_module_valid_typer(self) -> None:
        import types

        module = types.ModuleType("test_module")
        module.bakebook = Bakebook()  # type: ignore[attr-defined]

        result = get_bakebook_from_module(module, DEFAULT_BAKEBOOK_NAME, Path("test.py"))
        assert isinstance(result, Bakebook)

    def test_get_bakebook_from_module_attribute_missing(self) -> None:
        import types

        module = types.ModuleType("test_module")

        with pytest.raises(BakebookError):
            get_bakebook_from_module(module, DEFAULT_BAKEBOOK_NAME, Path("test.py"))

    def test_get_bakebook_from_module_not_typer(self) -> None:
        import types

        module = types.ModuleType("test_module")
        module.bakebook = "not_a_typer_app"  # type: ignore[attr-defined]

        with pytest.raises(BakebookError):
            get_bakebook_from_module(module, DEFAULT_BAKEBOOK_NAME, Path("test.py"))


class TestGetBakebookFromTargetDirPath:
    def test_get_bakebook_from_target_dir_path_valid(self, tmp_path: Path) -> None:
        bakefile_path = tmp_path / DEFAULT_FILE_NAME
        bakefile_path.write_text("from bake import Bakebook\nbakebook = Bakebook()\n")

        result = get_bakebook_from_target_dir_path(bakefile_path, DEFAULT_BAKEBOOK_NAME)
        assert isinstance(result, Bakebook)

    def test_get_bakebook_from_target_dir_path_invalid_filename(self, tmp_path: Path) -> None:
        fake_path = tmp_path / "nonexistent.py"
        # load_module will fail because the file doesn't exist
        with pytest.raises((BakebookError, FileNotFoundError)):
            get_bakebook_from_target_dir_path(fake_path, DEFAULT_BAKEBOOK_NAME)
