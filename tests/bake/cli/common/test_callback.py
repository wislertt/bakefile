import pytest
import typer

from bake.cli.common.callback import validate_file_name, validate_file_name_callback
from bake.utils.constants import DEFAULT_FILE_NAME


class TestValidateFileName:
    def test_validate_file_name_valid(self) -> None:
        result = validate_file_name(DEFAULT_FILE_NAME)
        assert result == DEFAULT_FILE_NAME

    @pytest.mark.parametrize(
        "file_name",
        [f"some/path/{DEFAULT_FILE_NAME}", rf"some\path\{DEFAULT_FILE_NAME}", "bake.txt"],
    )
    def test_validate_file_name_invalid(self, file_name: str) -> None:
        with pytest.raises(typer.BadParameter):
            validate_file_name(file_name)


class TestValidateFileNameCallback:
    def test_validate_file_name_callback_valid(self) -> None:
        result = validate_file_name_callback(DEFAULT_FILE_NAME)
        assert result == DEFAULT_FILE_NAME

    @pytest.mark.parametrize(
        "file_name",
        [f"some/path/{DEFAULT_FILE_NAME}", rf"some\path\{DEFAULT_FILE_NAME}", "bake.txt"],
    )
    def test_validate_file_name_callback_invalid(self, file_name: str) -> None:
        with pytest.raises(typer.BadParameter):
            validate_file_name_callback(file_name)
