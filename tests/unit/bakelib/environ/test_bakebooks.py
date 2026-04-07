import inspect

import pytest

from bakelib.environ import EnvBakebook, EnvBakebooks
from bakelib.environ.base import BaseEnv
from bakelib.environ.get import get_bakebook


class _DevBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("dev")


class _StagingBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("staging")


class _ProdBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("prod")


class TestBakebooks:
    def test_collects_all_env_bakebook_instances(self):
        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            staging = _StagingBakebook()
            prod = _ProdBakebook()

        result = MyBakebooks.all()
        assert len(result) == 3
        assert all(isinstance(bb, EnvBakebook) for bb in result)

    def test_ignores_non_bakebook_attributes(self):
        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            some_string = "not a bakebook"
            some_number = 42

        result = MyBakebooks.all()
        assert len(result) == 1

    def test_empty_class_returns_empty_list(self):
        class EmptyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            pass

        assert EmptyBakebooks.all() == []


class TestDirectAccess:
    def test_access_bakebook_by_attribute(self):
        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            prod = _ProdBakebook()

        assert isinstance(MyBakebooks.dev, _DevBakebook)
        assert isinstance(MyBakebooks.prod, _ProdBakebook)
        assert str(MyBakebooks.dev.env) == "dev"


class TestGetBakebook:
    def test_delegates_to_get_bakebook(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENV", "dev")

        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            prod = _ProdBakebook()

        result = MyBakebooks.get()
        assert result is MyBakebooks.dev

    def test_empty_class_raises_error(self):
        class EmptyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            pass

        with pytest.raises(ValueError, match="bakebooks list cannot be empty"):
            EmptyBakebooks.get()

    def test_forwards_kwargs(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MY_ENV", "prod")

        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            prod = _ProdBakebook()

        result = MyBakebooks.get(env_var_name="MY_ENV")
        assert result is MyBakebooks.prod


class TestSignatureParity:
    def test_get_signature_matches_environ_get_bakebook(self):
        cls_sig = inspect.signature(EnvBakebooks.get)
        fn_sig = inspect.signature(get_bakebook)

        cls_params = list(cls_sig.parameters.keys())
        fn_params = list(fn_sig.parameters.keys())

        # Class method should have all params except 'bakebooks'
        assert cls_params == fn_params[1:]  # skip first param 'bakebooks'

        # Verify defaults match
        for param_name in cls_params:
            cls_default = cls_sig.parameters[param_name].default
            fn_default = fn_sig.parameters[param_name].default
            assert cls_default == fn_default, f"Default mismatch for '{param_name}'"


class TestValidation:
    def test_matching_env_code_passes(self):
        class MyBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
            dev = _DevBakebook()
            prod = _ProdBakebook()

        # Should not raise
        assert MyBakebooks.all()

    def test_mismatched_env_code_raises_value_error(self):
        with pytest.raises(
            ValueError, match="Attribute 'wrong_name' has env='dev', expected env='wrong_name'"
        ):

            class _BadBakebooks(EnvBakebooks[EnvBakebook[BaseEnv]]):
                wrong_name = _DevBakebook()

    def test_type_mismatch_caught_when_parameterized(self):
        """Runtime validation: wrong type E is caught via __orig_bases__."""

        with pytest.raises(
            TypeError, match="Attribute 'prod' has type _ProdBakebook, expected _DevBakebook"
        ):

            class _BadTypeBakebooks(EnvBakebooks[_DevBakebook]):
                dev = _DevBakebook()
                prod = _ProdBakebook()

    def test_no_type_check_when_not_parameterized(self):
        """Without [E], type validation is skipped gracefully."""

        class _Unparameterized(EnvBakebooks):
            dev = _DevBakebook()
            prod = _ProdBakebook()

        # Should not raise
        assert len(_Unparameterized.all()) == 2

    def test_subclass_of_subclass_still_validates_type(self):
        """Type validation propagates through indirect inheritance."""

        class _Parent(EnvBakebooks[_DevBakebook]):
            dev = _DevBakebook()

        with pytest.raises(
            TypeError, match="Attribute 'prod' has type _ProdBakebook, expected _DevBakebook"
        ):

            class _Child(_Parent):
                prod = _ProdBakebook()
