from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from bakefile.cli.bake.resolve_bakebook import (
    change_directory,
    get_bakebook,
    load_module,
    resolve_bakebook,
    resolve_file_path,
    validate_file_name,
)
from bakefile.exceptions import BakebookError


class TestChangeDirectory:
    def test_change_directory_valid(self, tmp_path: Path) -> None:
        change_directory(str(tmp_path))
        import os

        assert os.getcwd() == str(tmp_path)

    @pytest.mark.parametrize(
        "path",
        ["", "   ", "/nonexistent/path/12345"],
    )
    def test_change_directory_invalid_path(self, path: str) -> None:
        with pytest.raises(BakebookError):
            change_directory(path)

    def test_change_directory_not_a_directory(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(BakebookError):
            change_directory(str(file_path))


class TestValidateFileName:
    def test_validate_file_name_valid(self) -> None:
        validate_file_name("bakefile.py")

    @pytest.mark.parametrize(
        "file_name",
        ["some/path/bakefile.py", r"some\path\bakefile.py", "bakefile.txt"],
    )
    def test_validate_file_name_invalid(self, file_name: str) -> None:
        with pytest.raises(BakebookError):
            validate_file_name(file_name)


class TestResolveFilePath:
    def test_resolve_file_path_valid(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.py"
        file_path.write_text("print('test')")

        import os

        os.chdir(tmp_path)
        result = resolve_file_path("test.py")
        assert result == file_path

    def test_resolve_file_path_not_found(self) -> None:
        with pytest.raises(BakebookError):
            resolve_file_path("nonexistent.py")


class TestLoadModule:
    def test_load_module_valid(self, tmp_path: Path) -> None:
        module_path = tmp_path / "test_module.py"
        module_path.write_text("value = 42")

        module = load_module(module_path)
        assert hasattr(module, "value")
        assert module.value == 42

    def test_load_module_none_spec(self) -> None:
        with patch(
            "bakefile.cli.bake.resolve_bakebook.importlib.util.spec_from_file_location",
            return_value=None,
        ):
            fake_path = Path("fake.py")
            with pytest.raises(BakebookError):
                load_module(fake_path)


class TestGetBakebook:
    def test_get_bakebook_valid_typer(self) -> None:
        import types

        module = types.ModuleType("test_module")
        module.bakebook = typer.Typer()  # type: ignore[attr-defined]

        result = get_bakebook(module, "bakebook", Path("test.py"))
        assert isinstance(result, typer.Typer)

    def test_get_bakebook_attribute_missing(self) -> None:
        import types

        module = types.ModuleType("test_module")

        with pytest.raises(BakebookError):
            get_bakebook(module, "bakebook", Path("test.py"))

    def test_get_bakebook_not_typer(self) -> None:
        import types

        module = types.ModuleType("test_module")
        module.bakebook = "not_a_typer_app"  # type: ignore[attr-defined]

        with pytest.raises(BakebookError):
            get_bakebook(module, "bakebook", Path("test.py"))


class TestResolveBakebook:
    def test_resolve_bakebook_with_chdir(self, examples_simple_dir: Path) -> None:
        result = resolve_bakebook("bakefile.py", "bakebook", str(examples_simple_dir))
        assert isinstance(result, typer.Typer)

    def test_resolve_bakebook_without_chdir(self, tmp_path: Path) -> None:
        import os

        os.chdir(tmp_path)
        (tmp_path / "bakefile.py").write_text("import typer\nbakebook = typer.Typer()\n")

        result = resolve_bakebook("bakefile.py", "bakebook", None)
        assert isinstance(result, typer.Typer)

    def test_resolve_bakebook_invalid_chdir(self) -> None:
        with pytest.raises(BakebookError):
            resolve_bakebook("bakefile.py", "bakebook", "/nonexistent")

    def test_resolve_bakebook_invalid_filename(self, examples_simple_dir: Path) -> None:
        with pytest.raises(BakebookError):
            resolve_bakebook("invalid.txt", "bakebook", str(examples_simple_dir))
