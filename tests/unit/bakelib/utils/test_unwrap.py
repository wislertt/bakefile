"""Tests for unwrap function."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from bakelib.utils import unwrap


class TestUnwrapBasicTypes:
    """Test unwrap with basic types."""

    def test_unwrap_with_str(self):
        """Should work with str type."""
        my_str: str | None = "hello"
        result: str = unwrap(my_str)
        assert result == "hello"
        assert result.upper() == "HELLO"  # Type narrowed to str

    def test_unwrap_with_int(self):
        """Should work with int type."""
        my_int: int | None = 42
        result: int = unwrap(my_int)
        assert result == 42
        assert result.bit_length() > 0  # int method works

    def test_unwrap_with_bool(self):
        """Should work with bool type."""
        my_bool: bool | None = True
        result: bool = unwrap(my_bool)
        assert result is True

    def test_unwrap_with_float(self):
        """Should work with float type."""
        my_float: float | None = 3.14
        result: float = unwrap(my_float)
        assert result == 3.14

    def test_unwrap_with_list(self):
        """Should work with list type."""
        my_list: list[str] | None = ["a", "b", "c"]
        result: list[str] = unwrap(my_list)
        assert result == ["a", "b", "c"]
        assert len(result) == 3

    def test_unwrap_with_dict(self):
        """Should work with dict type."""
        my_dict: dict[str, int] | None = {"a": 1, "b": 2}
        result: dict[str, int] = unwrap(my_dict)
        assert result == {"a": 1, "b": 2}
        assert result["a"] == 1


class TestUnwrapEdgeCases:
    """Test unwrap edge cases."""

    def test_unwrap_preserves_falsy_values(self):
        """Should not raise on falsy values that are not None."""
        zero: int | None = 0
        empty_str: str | None = ""
        false_bool: bool | None = False
        empty_list: list[str] | None = []
        empty_dict: dict[str, int] | None = {}

        result_zero: int = unwrap(zero)
        result_str: str = unwrap(empty_str)
        result_bool: bool = unwrap(false_bool)
        result_list: list[str] = unwrap(empty_list)
        result_dict: dict[str, int] = unwrap(empty_dict)

        assert result_zero == 0
        assert result_str == ""
        assert result_bool is False
        assert result_list == []
        assert result_dict == {}

    def test_unwrap_raises_on_none_with_variable(self):
        """Should raise ValueError when value is None from variable."""
        my_none: str | None = None
        with pytest.raises(
            ValueError,
            match=(
                r"called `unwrap\(\)` on a `None` value, "
                r"tests[/\\]unit[/\\]bakelib[/\\]utils[/\\]test_unwrap\.py:\d+"
            ),
        ):
            unwrap(my_none)

    def test_unwrap_raises_on_none_directly(self):
        """Should raise Rust-style error when None passed directly."""
        with pytest.raises(
            ValueError,
            match=(
                r"called `unwrap\(\)` on a `None` value, "
                r"tests[/\\]unit[/\\]bakelib[/\\]utils[/\\]test_unwrap\.py:\d+"
            ),
        ):
            unwrap(None)

    def test_unwrap_with_non_nullable_type(self):
        """Should work even if type hint says non-nullable (runtime doesn't enforce)."""
        non_nullable: str = "hello"  # Type is str, not str | None
        result = unwrap(non_nullable)
        assert result == "hello"

    def test_unwrap_with_custom_class(self):
        """Should work with custom objects."""

        class CustomClass:
            def __init__(self, value: str):
                self.value = value

        my_obj: CustomClass | None = CustomClass("test")
        result = unwrap(my_obj)
        assert result.value == "test"

    def test_unwrap_from_different_cwd_shows_full_path(self, tmp_path):
        """Should show full path when called from a different CWD."""
        original_cwd = Path.cwd()
        # Get the test file name to verify it appears in the error
        test_file_name = Path(__file__).name

        try:
            # Change to temp directory so test file is outside CWD
            import os

            os.chdir(tmp_path)

            # This should now show full path since we're in a different directory
            # Check that it contains the test file name (not relative path)
            with pytest.raises(ValueError) as exc_info:
                unwrap(None)

            error_msg = str(exc_info.value)
            # Verify the error contains the test file name
            assert test_file_name in error_msg
            # Verify it's NOT a relative path (doesn't start with "tests/")
            assert not error_msg.split(", ")[-1].startswith("tests/")
        finally:
            # Restore original CWD
            os.chdir(original_cwd)


class TestUnwrapInspection:
    """Test unwrap's automatic variable name detection."""

    class Demo(BaseModel):
        ar_docker_region_name: str | None = None
        ar_docker_project_id: str | None = None

        def get_region(self) -> str:
            return unwrap(self.ar_docker_region_name)

        def get_project(self) -> str:
            return unwrap(self.ar_docker_project_id)

    def test_includes_variable_name_in_error_message(self):
        """Should include file location in the error message (Rust-style)."""
        demo = self.Demo(ar_docker_region_name="us-central1")

        with pytest.raises(
            ValueError,
            match=(
                r"called `unwrap\(\)` on a `None` value, "
                r"tests[/\\]unit[/\\]bakelib[/\\]utils[/\\]test_unwrap\.py:\d+"
            ),
        ):
            demo.get_project()

    def test_works_when_all_fields_present(self):
        """Should return values when all fields are present."""
        demo = self.Demo(
            ar_docker_region_name="us-central1",
            ar_docker_project_id="my-project",
        )
        assert demo.get_region() == "us-central1"
        assert demo.get_project() == "my-project"


class TestUnwrapManyVariables:
    """Test unwrap with many variables - like get_ar_docker_remote_image_url."""

    class DockerConfig(BaseModel):
        ar_docker_region_name: str | None = None
        ar_docker_project_id: str | None = None
        ar_docker_repo_name: str | None = None
        ar_docker_project_description: str | None = None
        ar_docker_image_name: str | None = None

        def get_url(self) -> str:
            """Build URL using unwrap for all required fields."""
            region = unwrap(self.ar_docker_region_name)
            project = unwrap(self.ar_docker_project_id)
            repo = unwrap(self.ar_docker_repo_name)
            description = unwrap(self.ar_docker_project_description)
            image = unwrap(self.ar_docker_image_name)

            return f"{region}-docker.pkg.dev/{project}/{repo}/{description}/{image}"

    def test_works_with_many_unwraps(self):
        """Should handle multiple unwrap calls in one method."""
        config = self.DockerConfig(
            ar_docker_region_name="us-central1",
            ar_docker_project_id="my-project",
            ar_docker_repo_name="my-repo",
            ar_docker_project_description="docker-run",
            ar_docker_image_name="my-image",
        )

        result = config.get_url()
        assert result == "us-central1-docker.pkg.dev/my-project/my-repo/docker-run/my-image"

    def test_fails_on_first_none_with_var_name(self):
        """Should fail on the first None and include file location (Rust-style)."""
        config = self.DockerConfig(
            ar_docker_region_name="us-central1",
            # ar_docker_project_id is missing - should be the first failure
        )

        with pytest.raises(
            ValueError,
            match=(
                r"called `unwrap\(\)` on a `None` value, "
                r"tests[/\\]unit[/\\]bakelib[/\\]utils[/\\]test_unwrap\.py:\d+"
            ),
        ):
            config.get_url()
