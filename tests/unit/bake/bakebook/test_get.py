from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bake import Bakebook
from bake.bakebook.get import (
    get_bakebook_from_module,
    get_bakebook_from_target_dir_path,
    get_target_dir_path,
    load_module,
    resolve_bakefile_path,
    retry_load_module_with_uv_sync,
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

    def test_load_module_none_loader(self, tmp_path: Path) -> None:
        module_path = tmp_path / "test_module.py"
        module_path.write_text("value = 42")

        mock_spec = MagicMock()
        mock_spec.loader = None

        with (
            patch(
                "bake.bakebook.get.importlib.util.spec_from_file_location",
                return_value=mock_spec,
            ),
            pytest.raises(BakebookError, match="Failed to load"),
        ):
            load_module(module_path)

    def test_load_module_import_error_calls_retry(self, tmp_path: Path) -> None:
        module_path = tmp_path / "test_module.py"
        module_path.write_text("import nonexistent_module")

        with patch("bake.bakebook.get.retry_load_module_with_uv_sync") as mock_retry:
            load_module(module_path)
            mock_retry.assert_called_once()
            args = mock_retry.call_args[1]
            assert args["target_dir_path"] == module_path
            assert isinstance(args["error"], ImportError)
            assert args["parent_dir"] == str(tmp_path)
            assert args["module"] is not None

    def test_load_module_generic_exception_raises_bakebook_error(self, tmp_path: Path) -> None:
        module_path = tmp_path / "test_module.py"
        module_path.write_text("raise ValueError('test error')")

        with pytest.raises(BakebookError, match="Failed get bakebook from"):
            load_module(module_path)


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


class TestRetryLoadModuleWithUvSyncDryRun:
    def test_dry_run_standalone_bakefile(self, empty_project_folder: Path) -> None:
        import importlib.util

        bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
        parent_dir = str(empty_project_folder)

        error = ImportError("No module named 'test_package'", name="test_package")

        spec = importlib.util.spec_from_file_location("bakefile", bakefile_path)
        assert spec is not None and spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        loader_mock = MagicMock(spec=spec.loader)

        with patch("bake.bakebook.get.run_uv_sync") as mock_run_uv_sync:
            retry_load_module_with_uv_sync(
                target_dir_path=bakefile_path,
                error=error,
                parent_dir=parent_dir,
                loader=loader_mock,
                module=module,
                dry_run=True,
            )

            mock_run_uv_sync.assert_called_once_with(
                bakefile_path=bakefile_path,
                cmd=["--frozen"],
                dry_run=True,
            )
            loader_mock.exec_module.assert_called_once_with(module)

    def test_dry_run_project_level_bakefile(self, uv_project_folder_without_dep: Path) -> None:
        import importlib.util

        bakefile_path = uv_project_folder_without_dep / DEFAULT_FILE_NAME
        parent_dir = str(uv_project_folder_without_dep)

        error = ImportError("No module named 'test_package'", name="test_package")

        spec = importlib.util.spec_from_file_location("bakefile", bakefile_path)
        assert spec is not None and spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        loader_mock = MagicMock(spec=spec.loader)

        with patch("bake.bakebook.get.run_uv") as mock_run_uv:
            retry_load_module_with_uv_sync(
                target_dir_path=bakefile_path,
                error=error,
                parent_dir=parent_dir,
                loader=loader_mock,
                module=module,
                dry_run=True,
            )

            mock_run_uv.assert_called_once_with(
                ("sync", "--frozen", "--all-groups", "--all-extras"),
                cwd=parent_dir,
                capture_output=True,
                stream=True,
                check=True,
                echo=True,
                dry_run=True,
            )
            loader_mock.exec_module.assert_called_once_with(module)

    def test_dry_run_standalone_bakefile_exec_module_fails(
        self, empty_project_folder: Path
    ) -> None:
        import importlib.util

        bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
        parent_dir = str(empty_project_folder)

        error = ImportError("No module named 'missing_package'", name="missing_package")

        spec = importlib.util.spec_from_file_location("bakefile", bakefile_path)
        assert spec is not None and spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        loader_mock = MagicMock(spec=spec.loader)
        loader_mock.exec_module.side_effect = ImportError("Still missing dependency")

        with (
            patch("bake.bakebook.get.run_uv_sync") as mock_run_uv_sync,
            patch("bake.ui.console.error") as mock_console_error,
        ):
            with pytest.raises(BakebookError, match="Failed get bakebook from"):
                retry_load_module_with_uv_sync(
                    target_dir_path=bakefile_path,
                    error=error,
                    parent_dir=parent_dir,
                    loader=loader_mock,
                    module=module,
                    dry_run=True,
                )

            mock_run_uv_sync.assert_called_once_with(
                bakefile_path=bakefile_path,
                cmd=["--frozen"],
                dry_run=True,
            )
            mock_console_error.assert_called_once()
            assert "uv cache clean" in mock_console_error.call_args[0][0]
