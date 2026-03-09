from typing import ClassVar

import pytest
from pydantic import BaseModel, ValidationError

from bakelib.environ import BaseEnv


class TestBaseEnvInstantiation:
    @pytest.mark.parametrize("value", ["dev", "staging", "prod"])
    def test_create_env_from_valid_string(self, value: str):
        env = BaseEnv(value)
        assert str(env) == value
        assert isinstance(env, str)
        assert isinstance(env, BaseEnv)

    def test_env_is_subclass_of_str(self):
        assert issubclass(BaseEnv, str)

    def test_create_env_raises_error_for_invalid_value(self):
        with pytest.raises(
            ValueError,
            match=r"Invalid BaseEnv: 'invalid'. Must be one of: \['dev', 'staging', 'prod'\]",
        ):
            BaseEnv("invalid")


class TestBaseEnvComparison:
    def test_less_than_by_priority(self):
        # Priority order: dev < staging < prod
        assert BaseEnv("dev") < BaseEnv("staging")
        assert BaseEnv("dev") < BaseEnv("prod")
        assert BaseEnv("staging") < BaseEnv("prod")
        assert not (BaseEnv("prod") < BaseEnv("dev"))
        assert not (BaseEnv("dev") < BaseEnv("dev"))

    def test_comparison_chain(self):
        assert BaseEnv("dev") < BaseEnv("staging") < BaseEnv("prod")

    def test_greater_than_by_priority(self):
        assert BaseEnv("prod") > BaseEnv("staging")
        assert BaseEnv("prod") > BaseEnv("dev")
        assert BaseEnv("staging") > BaseEnv("dev")
        assert not (BaseEnv("dev") > BaseEnv("prod"))

    @pytest.mark.parametrize("method", ["__lt__", "__le__", "__gt__", "__ge__"])
    def test_comparison_returns_not_implemented_for_non_env(self, method: str):
        env = BaseEnv("dev")
        result = getattr(env, method)(123)
        assert result is NotImplemented


class TestBaseEnvEquality:
    def test_equals_same_value(self):
        assert BaseEnv("dev") == BaseEnv("dev")
        assert BaseEnv("dev") != "dev"

    def test_not_equal_different_values(self):
        assert BaseEnv("dev") != BaseEnv("prod")
        assert BaseEnv("dev") != "prod"
        assert BaseEnv("dev") != 123
        assert BaseEnv("dev") is not None

    def test_case_sensitive(self):
        class UnrestrictedEnv(BaseEnv):
            ENV_ORDER: ClassVar[list[str | set[str]]] = ["dev", "DEV", "Dev"]

        assert UnrestrictedEnv("dev") != UnrestrictedEnv("DEV")
        assert UnrestrictedEnv("dev") != "DEV"


class TestBaseEnvComparisonCrossClass:
    class CustomBaseEnv(BaseEnv): ...

    def test_comparison_returns_not_implemented_for_different_subclass(self):
        env = BaseEnv("dev")
        custom = self.CustomBaseEnv("dev")

        assert env.__lt__(custom) is NotImplemented
        assert env.__le__(custom) is NotImplemented
        assert env.__gt__(custom) is NotImplemented
        assert env.__ge__(custom) is NotImplemented
        assert env.__eq__(custom) is False


class TestBaseEnvHash:
    def test_hash_matches_string_hash(self):
        assert hash(BaseEnv("dev")) == hash("dev")
        assert hash(BaseEnv("dev")) != hash(BaseEnv("prod"))

    def test_env_can_be_used_in_set(self):
        envs = {BaseEnv("dev"), BaseEnv("prod"), "dev"}
        assert len(envs) == 3
        assert BaseEnv("prod") in envs

    def test_env_can_be_used_as_dict_key(self):
        d: dict[str | BaseEnv, str] = {BaseEnv("dev"): "development", BaseEnv("prod"): "production"}
        assert d[BaseEnv("dev")] == "development"
        with pytest.raises(KeyError):
            assert d["dev"] == "development"
        assert len(d) == 2


class TestBaseEnvRepr:
    @pytest.mark.parametrize("value", ["dev", "staging", "prod"])
    def test_repr_format(self, value: str):
        assert repr(BaseEnv(value)) == f"BaseEnv('{value}')"

    def test_repr_includes_class_name(self):
        class CustomBaseEnv(BaseEnv):
            pass

        assert repr(CustomBaseEnv("dev")) == "CustomBaseEnv('dev')"


class TestBaseEnvPydanticIntegration:
    def test_pydantic_model_with_env_field(self):
        class Model(BaseModel):
            env: BaseEnv

        m = Model(env="dev")  # type: ignore[arg-type]
        assert isinstance(m.env, BaseEnv)
        assert str(m.env) == "dev"

    def test_pydantic_accepts_env_instance(self):
        class Model(BaseModel):
            env: BaseEnv

        m = Model(env=BaseEnv("prod"))
        assert str(m.env) == "prod"

    def test_pydantic_raises_error_for_invalid_value(self):
        class Model(BaseModel):
            env: BaseEnv

        with pytest.raises(ValidationError):
            Model(env="invalid")  # type: ignore[arg-type]

    def test_pydantic_optional_env_field(self):
        class Model(BaseModel):
            env: BaseEnv | None = None

        m1 = Model()
        assert m1.env is None

        m2 = Model(env="dev")  # type: ignore[arg-type]
        assert str(m2.env) == "dev"

    def test_pydantic_model_dump(self):
        class Model(BaseModel):
            env: BaseEnv

        m = Model(env="dev")  # type: ignore[arg-type]

        assert m.model_dump() == {"env": BaseEnv("dev")}
        assert m.model_dump() != {"env": "dev"}
        assert m.model_dump_json() != {"env": "dev"}


class TestBaseEnvValidate:
    def test_validate_returns_same_instance(self):
        env = BaseEnv("dev")
        result = BaseEnv.validate(env)
        assert result is env

    @pytest.mark.parametrize("value", ["dev", "staging"])
    def test_validate_converts_string(self, value: str):
        result = BaseEnv.validate(value)
        assert isinstance(result, BaseEnv)
        assert str(result) == value

    @pytest.mark.parametrize("invalid_value", [123, None, "invalid"])
    def test_validate_raises_error_for_invalid_input(self, invalid_value):
        with pytest.raises(ValueError):
            BaseEnv.validate(invalid_value)


class TestBaseEnvInheritance:
    class CustomBaseEnv(BaseEnv): ...

    def test_subclass_inherits_str_behavior(self):
        env = self.CustomBaseEnv("dev")
        assert str(env) == "dev"
        assert isinstance(env, str)
        assert isinstance(env, BaseEnv)
        assert isinstance(env, self.CustomBaseEnv)

    def test_subclass_has_own_repr(self):
        env = self.CustomBaseEnv("dev")
        assert repr(env) == "CustomBaseEnv('dev')"

    def test_subclass_with_pydantic(self):
        class Model(BaseModel):
            env: TestBaseEnvInheritance.CustomBaseEnv

        m = Model(env="dev")  # type: ignore[arg-type]
        assert isinstance(m.env, TestBaseEnvInheritance.CustomBaseEnv)


class TestBaseEnvEdgeCases:
    def test_env_order_with_sets_and_strings(self):
        class MixedEnv(BaseEnv):
            ENV_ORDER: ClassVar[list[str | set[str]]] = [
                "dev",
                {"staging", "qa"},  # Equal priority
                "prod",
            ]

        # Validation works for all values
        assert str(MixedEnv("dev")) == "dev"
        assert str(MixedEnv("staging")) == "staging"
        assert str(MixedEnv("qa")) == "qa"
        assert str(MixedEnv("prod")) == "prod"

        # Priority order: dev < {staging, qa} < prod
        assert MixedEnv("dev") < MixedEnv("staging")
        assert MixedEnv("dev") < MixedEnv("qa")
        assert MixedEnv("staging") < MixedEnv("prod")
        assert MixedEnv("qa") < MixedEnv("prod")

        # staging and qa have equal priority (same index)
        # Same priority uses alphabetical as tiebreaker: "qa" < "staging"
        assert MixedEnv("qa") < MixedEnv("staging")
        assert not (MixedEnv("staging") < MixedEnv("qa"))
        assert MixedEnv("qa") <= MixedEnv("staging")
        assert MixedEnv("staging") >= MixedEnv("qa")

    def test_flattened_env_order_sorts_set_items(self):
        class UnsortedSetEnv(BaseEnv):
            # Set with items in non-alphabetical order
            ENV_ORDER: ClassVar[list[str | set[str]]] = [
                "zulu",
                {"delta", "alpha", "charlie"},  # Unsorted set
                "bravo",
            ]

        # _flattened_env_order should return sorted items from the set
        flattened = UnsortedSetEnv._flattened_env_order()
        assert flattened == ["zulu", "alpha", "charlie", "delta", "bravo"]

    def test_env_with_unicode(self):
        class UnicodeEnv(BaseEnv):
            ENV_ORDER: ClassVar[list[str | set[str]]] = ["devë"]

        env = UnicodeEnv("devë")
        assert str(env) == "devë"
        assert hash(env) == hash("devë")

    def test_env_with_very_long_string(self):
        long_value = "a" * 1000

        class LongEnv(BaseEnv):
            ENV_ORDER: ClassVar[list[str | set[str]]] = [long_value]

        env = LongEnv(long_value)
        assert str(env) == long_value

    def test_multiple_instances_same_value(self):
        env1 = BaseEnv("dev")
        env2 = BaseEnv("dev")
        assert env1 == env2
        assert hash(env1) == hash(env2)

    def test_env_in_list(self):
        envs = [BaseEnv("dev"), BaseEnv("prod"), "staging"]
        assert BaseEnv("dev") in envs
        assert "dev" not in envs
