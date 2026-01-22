import pytest

from bakelib import EnvBakebook
from bakelib.environ import DevEnvBakebook, ProdEnvBakebook, StagingEnvBakebook
from bakelib.environ.get_bakebook import get_bakebook


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

        bbs: list[EnvBakebook] = [bb_dev, bb_prod]
        result = get_bakebook(bbs)
        assert result is bakebook_map[env_value]
        assert str(result.env) == env_value

    def test_falls_to_lowest_priority_when_env_unset(self):
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()

        assert bb_dev.env < bb_prod.env
        bbs: list[EnvBakebook] = [bb_dev, bb_prod]
        result = get_bakebook(bbs)
        assert result is bb_dev

    def test_raises_error_on_no_match(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENV", "staging")
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook] = [bb_dev, bb_prod]

        with pytest.raises(
            ValueError,
            match="No bakebook found with env='staging'",
        ):
            get_bakebook(bbs)

    def test_uses_custom_env_var_name(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MY_ENV", "prod")
        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook] = [bb_dev, bb_prod]

        result = get_bakebook(bbs, env_var_name="MY_ENV")
        assert result is bb_prod

    def test_handles_all_env_aware_bakebooks(self, monkeypatch: pytest.MonkeyPatch):
        bb_dev = DevEnvBakebook()
        bb_staging = StagingEnvBakebook()
        bb_prod = ProdEnvBakebook()
        bbs: list[EnvBakebook] = [bb_dev, bb_staging, bb_prod]

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
            get_bakebook([fake_bb, bb_dev])  # type: ignore[arg-type]
