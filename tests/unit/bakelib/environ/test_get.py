from typing import ClassVar

import pytest

from bakelib.environ import DevEnvBakebook, EnvBakebook, ProdEnvBakebook, StagingEnvBakebook
from bakelib.environ.base import BaseEnv
from bakelib.environ.get import get_bakebook


class TestGetBakebook:
    def test_raises_error_on_empty_list(self):
        with pytest.raises(ValueError, match="bakebooks list cannot be empty"):
            get_bakebook([])

    @pytest.mark.parametrize("env_value", ["dev", "prod"])
    def test_matches_exact_env_value(self, monkeypatch: pytest.MonkeyPatch, env_value: str):
        monkeypatch.setenv("ENV", env_value)
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        assert str(bb_dev.env) == "dev"
        assert str(bb_prod.env) == "prod"
        bakebook_map = {"dev": bb_dev, "prod": bb_prod}

        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_prod]
        result = get_bakebook(bbs)
        assert result is bakebook_map[env_value]
        assert str(result.env) == env_value

    def test_falls_to_lowest_priority_when_env_unset(self):
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()

        assert bb_dev.env < bb_prod.env
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_prod]
        result = get_bakebook(bbs)
        assert result is bb_dev

    def test_raises_error_on_no_match(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENV", "staging")
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_prod]

        with pytest.raises(
            ValueError,
            match="No bakebook found with env='staging'",
        ):
            get_bakebook(bbs)

    def test_uses_custom_env_var_name(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MY_ENV", "prod")
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_prod]

        result = get_bakebook(bbs, env_var_name="MY_ENV")
        assert result is bb_prod

    def test_handles_all_env_aware_bakebooks(self, monkeypatch: pytest.MonkeyPatch):
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging, bb_prod]

        # staging has higher priority (index 1) than prod (index 2)
        monkeypatch.setenv("ENV", "prod")
        result = get_bakebook(bbs)
        assert result is bb_prod
        assert str(result.env) == "prod"

        monkeypatch.setenv("ENV", "staging")
        result = get_bakebook(bbs)
        assert result is bb_staging
        assert str(result.env) == "staging"

    def test_raises_error_on_duplicate_env(self):
        bb_dev1 = DevEnvBakebook()
        bb_dev2 = DevEnvBakebook()

        with pytest.raises(ValueError, match="Duplicate env 'dev' found"):
            get_bakebook([bb_dev1, bb_dev2])

    def test_raises_error_on_missing_env_attribute(self):
        class FakeBakebook:
            pass

        fake_bb = FakeBakebook()
        bb_dev = DevEnvBakebook()

        with pytest.raises(ValueError, match="All bakebooks must have an 'env' attribute"):
            get_bakebook([fake_bb, bb_dev])  # ty: ignore[invalid-argument-type]


class TestGetBakebookLazyInit:
    def test_lazy_init_called_by_default(self):
        """lazy_init is called by default when selecting bakebook."""

        class CustomBakebook(DevEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomBakebook.lazy_init_called = True

        bb = CustomBakebook()
        result = get_bakebook([bb])

        assert result.lazy_init_called is True

    def test_lazy_init_false_skips_call(self):
        """lazy_init=False skips the lazy_init call."""

        class CustomBakebook(DevEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomBakebook.lazy_init_called = True

        bb = CustomBakebook()
        result = get_bakebook([bb], lazy_init=False)

        assert result.lazy_init_called is False

    def test_lazy_init_called_with_exact_env_match(self, monkeypatch: pytest.MonkeyPatch):
        """lazy_init is called when exact env match is found."""

        class CustomBakebook(ProdEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomBakebook.lazy_init_called = True

        bb_dev = DevEnvBakebook()
        bb_prod = CustomBakebook()
        monkeypatch.setenv("ENV", "prod")

        result = get_bakebook([bb_dev, bb_prod])

        assert result is bb_prod
        assert result.lazy_init_called is True

    def test_lazy_init_called_with_fallback_to_lowest_priority(self):
        """lazy_init is called when falling back to lowest priority."""

        class CustomBakebook(DevEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomBakebook.lazy_init_called = True

        bb_dev = CustomBakebook()
        bb_prod = ProdEnvBakebook()

        result = get_bakebook([bb_dev, bb_prod])

        assert result is bb_dev
        assert result.lazy_init_called is True

    def test_multiple_bakebooks_lazy_init_only_called_on_selected(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Only the selected bakebook has lazy_init called."""

        class CustomDev(DevEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomDev.lazy_init_called = True

        class CustomProd(ProdEnvBakebook):
            lazy_init_called: ClassVar[bool] = False

            def lazy_init(self) -> None:
                CustomProd.lazy_init_called = True

        bb_dev = CustomDev()
        bb_prod = CustomProd()
        monkeypatch.setenv("ENV", "prod")

        result = get_bakebook([bb_dev, bb_prod])

        assert result is bb_prod
        assert bb_prod.lazy_init_called is True
        assert bb_dev.lazy_init_called is False


class TestGetBakebookFallbackEnv:
    def test_fallback_env_value_used_when_env_unset(self):
        """fallback_env_value is used when ENV is not set."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs, fallback_env_value="staging")
        assert result is bb_staging
        assert str(result.env) == "staging"

    def test_fallback_env_value_used_when_env_empty(self):
        """fallback_env_value is used when ENV is empty string."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs, env_value="", fallback_env_value="staging")
        assert result is bb_staging
        assert str(result.env) == "staging"

    def test_env_value_takes_precedence_over_fallback(self):
        """env_value takes precedence over fallback_env_value."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs, env_value="dev", fallback_env_value="staging")
        assert result is bb_dev
        assert str(result.env) == "dev"

    def test_env_var_takes_precedence_over_fallback(self, monkeypatch: pytest.MonkeyPatch):
        """ENV var takes precedence over fallback_env_value."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]
        monkeypatch.setenv("ENV", "dev")

        result = get_bakebook(bbs, fallback_env_value="staging")
        assert result is bb_dev
        assert str(result.env) == "dev"

    def test_both_fallback_and_env_none_uses_min(self):
        """When both env_value and fallback_env_value are None, uses min."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs)
        assert result is bb_dev
        assert str(result.env) == "dev"

    def test_invalid_fallback_env_value_raises_error(self):
        """Invalid fallback_env_value raises ValueError."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        with pytest.raises(ValueError, match="No bakebook found with env='prod'"):
            get_bakebook(bbs, fallback_env_value="prod")

    def test_fallback_chain_env_none_fallback_valid_uses_fallback(self):
        """env_value=None, valid fallback_env_value → uses fallback."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs, env_value=None, fallback_env_value="staging")
        assert result is bb_staging

    def test_fallback_chain_env_empty_fallback_valid_uses_fallback(self):
        """env_value='', valid fallback_env_value → uses fallback."""
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bbs: list[EnvBakebook[BaseEnv]] = [bb_dev, bb_staging]

        result = get_bakebook(bbs, env_value="", fallback_env_value="staging")
        assert result is bb_staging
