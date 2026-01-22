"""Unit tests for EnvBakebook."""

import pytest

from bake.bakebook.bakebook import Bakebook
from bakelib.environ import BaseEnv, EnvBakebook
from bakelib.environ.bakebook import DevEnvBakebook, ProdEnvBakebook, StagingEnvBakebook


class TestEnvBakebook:
    def test_create_env_bakebook_with_env(self):
        bb = EnvBakebook(env_=BaseEnv("dev"))
        assert bb.env == BaseEnv("dev")

    def test_create_env_bakebook_without_env_raises_error(self):
        with pytest.raises(ValueError):
            EnvBakebook()  # type: ignore[call-arg]

    def test_env_bakebook_inherits_from_bakebook(self):
        assert issubclass(EnvBakebook, Bakebook)
        assert isinstance(EnvBakebook(env_=BaseEnv("dev")), Bakebook)

    def test_env_bakebook_env_comparison(self):
        bb_dev = EnvBakebook(env_=BaseEnv("dev"))
        bb_prod = EnvBakebook(env_=BaseEnv("prod"))
        assert bb_dev.env < bb_prod.env

        bb_dev = DevEnvBakebook()
        bb_prod = ProdEnvBakebook()
        assert bb_dev.env < bb_prod.env


class TestEnvSpecificBakebooks:
    @pytest.mark.parametrize(
        "bakebook_class,expected_env",
        [
            (DevEnvBakebook, "dev"),
            (StagingEnvBakebook, "staging"),
            (ProdEnvBakebook, "prod"),
        ],
    )
    def test_env_bakebook_defaults_to_correct_env(self, bakebook_class, expected_env):
        bb = bakebook_class()
        assert str(bb.env) == expected_env
        assert isinstance(bb, EnvBakebook)
