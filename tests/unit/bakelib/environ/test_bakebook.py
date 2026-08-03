"""Unit tests for EnvBakebook."""

from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from bake.bakebook.bakebook import Bakebook
from bakelib.environ import BaseEnv, EnvBakebook
from bakelib.environ.bakebook import (
    _ExcludeEnvFieldSource,
)
from bakelib.environ.presets import GcpLandingZoneEnv
from tests.utils.bakebook import DevEnvBB, ProdEnvBB, StagingEnvBB


class TestExcludeEnvFieldSource:
    """Tests for _ExcludeEnvFieldSource wrapper."""

    def test_get_field_value_delegates_to_source(self):
        """Test that get_field_value delegates to the wrapped source."""

        class MockSettings(BaseSettings):
            pass

        mock_source = MagicMock(spec=PydanticBaseSettingsSource)
        mock_source.get_field_value.return_value = ("value", "key", True)

        wrapper = _ExcludeEnvFieldSource(mock_source, MockSettings)
        field = Field(description="test field")
        result = wrapper.get_field_value(field, "test_field")

        assert result == ("value", "key", True)
        mock_source.get_field_value.assert_called_once_with(field, "test_field")

    def test_call_excludes_env_field(self):
        """Test that __call__ filters out 'env' field from source."""

        class MockSettings(BaseSettings):
            pass

        mock_source = MagicMock(spec=PydanticBaseSettingsSource)
        mock_source.return_value = {"env": "dev", "other": "value", "another": 123}

        wrapper = _ExcludeEnvFieldSource(mock_source, MockSettings)
        result = wrapper()

        assert result == {"other": "value", "another": 123}
        assert "env" not in result
        mock_source.assert_called_once()

    def test_call_with_no_env_field_unchanged(self):
        """Test that __call__ passes through when no 'env' field present."""

        class MockSettings(BaseSettings):
            pass

        mock_source = MagicMock(spec=PydanticBaseSettingsSource)
        mock_source.return_value = {"other": "value", "another": 123}

        wrapper = _ExcludeEnvFieldSource(mock_source, MockSettings)
        result = wrapper()

        assert result == {"other": "value", "another": 123}
        mock_source.assert_called_once()


class TestEnvBakebook:
    def test_create_env_bakebook_with_env(self):
        bb = EnvBakebook(env=BaseEnv("dev"))
        assert bb.env == BaseEnv("dev")

    def test_create_env_bakebook_without_env_raises_error(self):
        with pytest.raises(ValueError):
            EnvBakebook()

    def test_env_bakebook_inherits_from_bakebook(self):
        assert issubclass(EnvBakebook, Bakebook)
        assert isinstance(EnvBakebook(env=BaseEnv("dev")), Bakebook)

    def test_env_bakebook_env_comparison(self):
        bb_dev = EnvBakebook(env=BaseEnv("dev"))
        bb_prod = EnvBakebook(env=BaseEnv("prod"))
        assert bb_dev.env < bb_prod.env

        assert DevEnvBB().env < ProdEnvBB().env

    def test_env_included_in_model_dump(self):
        bb = DevEnvBB()
        dump = bb.model_dump()

        assert "env" in dump
        assert dump["env"] == BaseEnv("dev")
        assert str(dump["env"]) == "dev"

    def test_env_bakebook_skips_auto_lazy_init_on_construction(self) -> None:
        class CustomDev(DevEnvBB):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomDev.lazy_init_called = True

        CustomDev()
        assert CustomDev.lazy_init_called is False


class TestEnvSpecificBakebooks:
    @pytest.mark.parametrize(
        "bakebook_class,expected_env",
        [
            (DevEnvBB, "dev"),
            (StagingEnvBB, "staging"),
            (ProdEnvBB, "prod"),
        ],
    )
    def test_env_bakebook_defaults_to_correct_env(self, bakebook_class, expected_env):
        bb = bakebook_class()
        assert str(bb.env) == expected_env


class TestEnvBakebookEnvPrefix:
    """Tests that env field is excluded from .env reading even with custom prefix."""

    def test_env_field_excluded_with_custom_prefix(self, monkeypatch: pytest.MonkeyPatch):
        """Test that 'env' field is not read from ENV even with env_prefix set."""

        class CustomBakebook(EnvBakebook[BaseEnv]):
            model_config = SettingsConfigDict(env_prefix="CUSTOM_")

            env: BaseEnv = BaseEnv("dev")
            other: str = "default_other"

        # Set environment variables with CUSTOM_ prefix
        monkeypatch.setenv("CUSTOM_ENV", "prod")
        monkeypatch.setenv("CUSTOM_OTHER", "from_env_other")

        bb = CustomBakebook()

        # env should use "dev" (default), not "prod" from CUSTOM_ENV
        assert str(bb.env) == "dev"
        # other should be read from CUSTOM_OTHER
        assert bb.other == "from_env_other"


class TestEnvBakebookDotEnvFile:
    """Integration tests with real .env files in temporary folders."""

    def test_env_field_excluded_from_dotenv_file(self, tmp_path: Path):
        """Test that 'env' field is not read from .env file."""

        class TestBakebook(EnvBakebook[BaseEnv]):
            model_config = SettingsConfigDict(env_file=str(tmp_path / ".env"))

            env: BaseEnv = BaseEnv("dev")
            other: str = "default_other"
            another: int = 999

        # Create .env file with env field
        env_file = tmp_path / ".env"
        env_file.write_text("ENV=prod\nOTHER=from_dotenv\nANOTHER=111\n")

        bb = TestBakebook()

        # env should use "dev" (default), not "prod" from .env file
        assert str(bb.env) == "dev"
        # other and another should be read from .env file
        assert bb.other == "from_dotenv"
        assert bb.another == 111

    def test_env_field_excluded_from_dotenv_file_with_secrets(self, tmp_path: Path):
        """Test that 'env' field is not read from .env file or secrets directory."""

        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()

        class TestBakebook(EnvBakebook[BaseEnv]):
            model_config = SettingsConfigDict(
                env_file=str(tmp_path / ".env"), secrets_dir=str(secrets_dir)
            )

            env: BaseEnv = BaseEnv("dev")
            api_key: str = "default_key"

        # Create .env file with env field
        env_file = tmp_path / ".env"
        env_file.write_text("ENV=staging\nAPI_KEY=from_dotenv\n")

        # Create secrets file (for env field)
        env_secret = secrets_dir / "env"
        env_secret.write_text("prod")

        bb = TestBakebook()

        # env should use "dev" (default), not from .env file or secrets
        assert str(bb.env) == "dev"
        # api_key should come from .env file
        assert bb.api_key == "from_dotenv"


class TestEnvTypeValidation:
    def test_raises_error_when_env_type_mismatches_generic_param(self):
        """Defining a subclass with wrong env type raises TypeError at class creation."""
        with pytest.raises(
            TypeError,
            match="'_BadEnvBakebook\\.env' annotation is BaseEnv, expected GcpLandingZoneEnv",
        ):

            class _BadEnvBakebook(EnvBakebook[GcpLandingZoneEnv]):
                env: BaseEnv = BaseEnv("dev")

    def test_valid_when_env_matches_generic_param(self):
        """Subclass with correct env type passes validation."""

        class _GoodEnvBakebook(EnvBakebook[GcpLandingZoneEnv]):
            env: GcpLandingZoneEnv = GcpLandingZoneEnv("d")

        bb = _GoodEnvBakebook()
        assert isinstance(bb.env, GcpLandingZoneEnv)

    def test_no_validation_when_not_parameterized(self):
        """Without [E], type validation is skipped."""

        class _Unparameterized(EnvBakebook):
            env: BaseEnv = BaseEnv("dev")

        assert str(_Unparameterized().env) == "dev"
