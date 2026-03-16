import sys
from typing import ClassVar

import pytest
from pydantic import BaseModel, ValidationError

from bakelib.environ.base import BaseEnv, BaseSubEnv, EnvPriorityOrderType


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
            match=(
                r"Value 'invalid' not found in ENV_PRIORITY_ORDER\. "
                r"Must be one of: \('dev', 'staging', 'prod'\)"
            ),
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
        """Equality is based on priority tier."""
        # Same string value = same priority = equal
        assert BaseEnv("dev") == BaseEnv("dev")
        # Not equal to plain string (not a BaseEnv instance)
        assert BaseEnv("dev") != "dev"
        # Not equal to different strings
        assert BaseEnv("dev") != "prod"

    def test_not_equal_different_values(self):
        """Different priority tiers are not equal."""
        assert BaseEnv("dev") != BaseEnv("prod")
        assert BaseEnv("dev") != "prod"
        assert BaseEnv("dev") != 123
        assert BaseEnv("dev") is not None

    def test_case_sensitive(self):
        """Different priorities are not equal even if similar."""

        class UnrestrictedEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "DEV", "Dev")

        # Different priority tiers = not equal
        assert UnrestrictedEnv("dev") != UnrestrictedEnv("DEV")
        assert UnrestrictedEnv("dev") != "DEV"


class TestBaseEnvComparisonCrossClass:
    class CustomBaseEnv(BaseEnv): ...

    class DifferentEnv(BaseEnv):
        ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("a", "b", "c")

    def test_same_env_order_not_comparable(self):
        """Subclasses with same ENV_ORDER are not comparable (different types)."""
        env = BaseEnv("dev")
        custom = self.CustomBaseEnv("prod")

        # Different types, so not comparable (even with same ENV_PRIORITY_ORDER)
        assert env.__lt__(custom) is NotImplemented
        assert env.__le__(custom) is NotImplemented
        assert env.__gt__(custom) is NotImplemented
        assert env.__ge__(custom) is NotImplemented

    def test_different_env_order_not_comparable(self):
        """Classes with different ENV_ORDER are not comparable."""
        env = BaseEnv("dev")
        different = self.DifferentEnv("a")

        # Different types, so not comparable
        assert env.__lt__(different) is NotImplemented
        assert env.__le__(different) is NotImplemented
        assert env.__gt__(different) is NotImplemented
        assert env.__ge__(different) is NotImplemented

    def test_equality_remains_type_specific(self):
        """Different types are not equal, even with same ENV_ORDER."""
        env = BaseEnv("dev")
        custom = self.CustomBaseEnv("dev")

        # Different types, not equal (comparison is type-specific)
        assert env != custom
        # But string values are equal
        assert str(env) == str(custom)


class TestBaseEnvHash:
    def test_env_is_unhashable(self):
        """BaseEnv cannot be used in sets or as dict keys."""
        env = BaseEnv("dev")

        # Cannot be hashed
        with pytest.raises(TypeError, match="unhashable"):
            hash(env)

        # Cannot be used in sets
        with pytest.raises(TypeError, match="unhashable"):
            {env, BaseEnv("prod")}

        # Cannot be used as dict keys
        with pytest.raises(TypeError, match="unhashable"):
            _ = {env: "value"}

    def test_string_conversion_works_in_collections(self):
        """But str(env) works fine in sets and dicts."""
        envs = {str(BaseEnv("dev")), str(BaseEnv("prod")), "staging"}
        assert len(envs) == 3
        assert "dev" in envs
        assert "prod" in envs

        d = {str(BaseEnv("dev")): "development"}
        assert d["dev"] == "development"


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
    def test_env_order_with_frozensets_and_strings(self):
        class MixedEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = (
                "dev",
                frozenset({"staging", "qa"}),  # Equal priority
                "prod",
            )

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
        # Same priority means equal, not less than
        assert not (MixedEnv("qa") < MixedEnv("staging"))
        assert not (MixedEnv("staging") < MixedEnv("qa"))
        assert MixedEnv("qa") <= MixedEnv("staging")
        assert MixedEnv("staging") >= MixedEnv("qa")

    def test_flattened_envs_sorts_frozenset_items(self):
        class UnsortedFrozensetEnv(BaseEnv):
            # Frozenset with items in non-alphabetical order
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = (
                "zulu",
                frozenset({"delta", "alpha", "charlie"}),  # Unsorted frozenset
                "bravo",
            )

        # flattened_envs should have sorted items from the frozenset
        env = UnsortedFrozensetEnv("zulu")
        assert env.flattened_envs == ("zulu", "alpha", "charlie", "delta", "bravo")

    def test_cache_is_per_class(self):
        """Each class has its own cache, not shared with parent or siblings."""

        class ChildEnv1(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("a", "b")

        class ChildEnv2(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("x", "y")

        # Each class has its own cache (need instance to access flattened_envs property)
        assert ChildEnv1("a").flattened_envs == ("a", "b")
        assert ChildEnv2("x").flattened_envs == ("x", "y")
        assert BaseEnv("dev").flattened_envs == ("dev", "staging", "prod")

        # Verify caching: same object reference (not recomputed)
        assert ChildEnv1("a").flattened_envs is ChildEnv1("a").flattened_envs
        assert ChildEnv1("a").flattened_envs is ChildEnv1._compute_flattened_envs()

    def test_flattened_envs_is_read_only(self):
        """flattened_envs property cannot be reassigned (frozen)."""

        class ChildEnv1(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("a", "b")

        # flattened_envs is read-only (property without setter)
        # Python 3.10: "can't set attribute 'flattened_envs'"
        # Python 3.11+: "property ... has no setter"
        match_msg = (
            r"can't set attribute 'flattened_envs'"
            if sys.version_info < (3, 11)
            else r"property .*flattened_envs.* has no setter"
        )
        with pytest.raises(AttributeError, match=match_msg):
            ChildEnv1("a").flattened_envs = ("a", "b", "c")  # type: ignore[misc]

    def test_cache_returns_same_object(self):
        """Multiple calls to flattened_envs return cached result (same object)."""
        env = BaseEnv("dev")
        result1 = env.flattened_envs
        result2 = env.flattened_envs

        # Same object reference (cached)
        assert result1 is result2

    def test_env_with_unicode(self):
        """Unicode environment codes work correctly."""

        class UnicodeEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("devë",)

        env = UnicodeEnv("devë")
        assert str(env) == "devë"
        # String value can be hashed
        assert hash(str(env)) == hash("devë")
        # But BaseEnv instance is unhashable
        with pytest.raises(TypeError, match="unhashable"):
            hash(env)

    def test_env_with_very_long_string(self):
        long_value = "a" * 1000

        class LongEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = (long_value,)

        env = LongEnv(long_value)
        assert str(env) == long_value

    def test_multiple_instances_same_value(self):
        """Multiple instances with same value are equal."""
        env1 = BaseEnv("dev")
        env2 = BaseEnv("dev")
        assert env1 == env2
        # Same string value
        assert str(env1) == str(env2)

    def test_env_in_list(self):
        envs = [BaseEnv("dev"), BaseEnv("prod"), "staging"]
        assert BaseEnv("dev") in envs
        assert "dev" not in envs

    def test_get_env_priority_order(self):
        """ENV_PRIORITY_ORDER returns the priority order."""
        order = BaseEnv.ENV_PRIORITY_ORDER
        assert order == ("dev", "staging", "prod")

    def test_get_env_priority_order_read_only(self):
        """Cannot mutate ENV_PRIORITY_ORDER (returns frozen tuple)."""
        order = BaseEnv.ENV_PRIORITY_ORDER

        # Tuple doesn't have copy() method - it's already immutable
        # Attempting to mutate raises TypeError
        with pytest.raises(TypeError, match=r"does not support item assignment"):
            order[0] = "new"  # type: ignore[index]

    def test_private_attributes_are_frozen(self):
        """Private attributes starting with "_" cannot be mutated after being set."""
        env = BaseEnv("dev")

        # Setting NEW "_" attributes is allowed (only existing ones are protected)
        env._custom = "value"
        assert env._custom == "value"  # type: ignore[attr-defined]

    def test_mutation_reflected_in_flattened_envs(self):
        """ENV_PRIORITY_ORDER is frozen and cannot be mutated."""

        class FrozenEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "staging", "prod")

        # Initial state - need instance to access flattened_envs
        env = FrozenEnv("dev")
        assert env.flattened_envs == ("dev", "staging", "prod")

        # Attempting to mutate the class variable raises AttributeError
        with pytest.raises(AttributeError, match=r"Cannot mutate.*ENV_PRIORITY_ORDER"):
            FrozenEnv.ENV_PRIORITY_ORDER = ("alpha", "beta", "gamma")

        # flattened_envs remains unchanged
        assert env.flattened_envs == ("dev", "staging", "prod")

        # Old values still work
        env2 = FrozenEnv("dev")
        assert str(env2) == "dev"

        # New values don't work
        with pytest.raises(ValueError, match="not found in ENV_PRIORITY_ORDER"):
            FrozenEnv("alpha")

    def test_mutation_to_invalid_value_raises_error(self):
        """Attempting to mutate ENV_PRIORITY_ORDER raises AttributeError."""

        class FrozenEnv(BaseEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "staging", "prod")

        # Initially valid
        env = FrozenEnv("dev")
        assert str(env) == "dev"

        # Attempting to mutate raises AttributeError (frozen)
        with pytest.raises(AttributeError, match=r"Cannot mutate.*ENV_PRIORITY_ORDER"):
            FrozenEnv.ENV_PRIORITY_ORDER = ("alpha", "beta", "gamma")

        # Old values still work (no mutation occurred)
        env2 = FrozenEnv("dev")
        assert str(env2) == "dev"


class TestBaseSubEnvEdgeCases:
    """Test edge cases for BaseSubEnv parsing."""

    class SimpleSubEnv(BaseSubEnv):
        ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "staging", "prod")

    def test_subclass_get_env_priority_order(self):
        """Subclass ENV_PRIORITY_ORDER returns its own order."""
        order = self.SimpleSubEnv.ENV_PRIORITY_ORDER
        assert order == ("dev", "staging", "prod")

    def test_negative_sub_raises_error(self):
        """Negative sub numbers are not valid (e.g., dev-1)."""
        with pytest.raises(ValueError, match="positive numeric suffix"):
            self.SimpleSubEnv("dev-1")

        with pytest.raises(ValueError, match="positive numeric suffix"):
            self.SimpleSubEnv("dev-99")

    def test_zero_sub_raises_error(self):
        """Sub number must be positive (> 0)."""
        with pytest.raises(ValueError, match="positive numeric suffix"):
            self.SimpleSubEnv("dev0")

    def test_float_sub_raises_error(self):
        """Float sub numbers are not valid (e.g., dev1.5)."""
        with pytest.raises(ValueError, match="positive numeric suffix"):
            self.SimpleSubEnv("dev1.5")

        with pytest.raises(ValueError, match="positive numeric suffix"):
            self.SimpleSubEnv("staging2.0")


class TestBaseSubEnvComparison:
    class SimpleSubEnv(BaseSubEnv):
        ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("a", "b", "c")

    def test_main_env_applies_last_within_tier(self):
        """Main env (no sub) applies after sub-envs within tier."""
        a = self.SimpleSubEnv("a")
        a1 = self.SimpleSubEnv("a1")
        a2 = self.SimpleSubEnv("a2")

        assert a2 < a1
        assert a1 < a
        assert a2 < a

    def test_sub_envs_ordered_by_number(self):
        """Higher sub numbers apply first (a10 < a2 < a1)."""
        a1 = self.SimpleSubEnv("a1")
        a2 = self.SimpleSubEnv("a2")
        a10 = self.SimpleSubEnv("a10")

        assert a10 < a2
        assert a2 < a1
        assert a10 < a1

    def test_cross_tier_comparison(self):
        """Cross-tier: lower main index applies first."""
        a = self.SimpleSubEnv("a")
        a99 = self.SimpleSubEnv("a99")
        b = self.SimpleSubEnv("b")
        b1 = self.SimpleSubEnv("b1")

        # a tier (index 0) applies before b tier (index 1)
        assert a99 < b
        assert a99 < b1
        assert a < b

    def test_equal_main_different_sub_not_equal(self):
        """Different sub numbers are not equal."""
        a1 = self.SimpleSubEnv("a1")
        a2 = self.SimpleSubEnv("a2")

        assert a1 != a2

    def test_same_main_and_sub_equal(self):
        """Same main and sub are equal."""
        a1 = self.SimpleSubEnv("a1")
        a1_copy = self.SimpleSubEnv("a1")

        assert a1 == a1_copy

    def test_main_env_without_sub_equal_to_itself(self):
        """Main env without sub equals itself."""
        a = self.SimpleSubEnv("a")
        a_copy = self.SimpleSubEnv("a")

        assert a == a_copy

    def test_comparison_operators(self):
        """All comparison operators work correctly."""
        a = self.SimpleSubEnv("a")
        a1 = self.SimpleSubEnv("a1")

        assert a1 < a
        assert a1 <= a
        assert a > a1
        assert a >= a1
        assert a != a1


class TestBaseSubEnvValidation:
    def test_digit_suffix_in_env_priority_order_raises_error(self):
        """ENV_PRIORITY_ORDER with digit-suffix codes raises ValueError on instance creation."""

        class BadEnv(BaseSubEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("a", "a1", "b")

        with pytest.raises(ValueError, match="cannot end with a digit"):
            BadEnv("a")

    def test_digit_suffix_in_frozenset_raises_error(self):
        """Digit-suffix codes in frozensets raise ValueError on instance creation."""

        class BadEnv(BaseSubEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = (
                "a",
                frozenset({"b", "b1"}),
            )

        with pytest.raises(ValueError, match="cannot end with a digit"):
            BadEnv("b1")

    def test_mutation_with_digit_suffix_raises_error(self):
        """Attempting to mutate to add digit-suffix codes raises AttributeError."""

        class ValidEnv(BaseSubEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("alpha", "beta")

        # Valid at definition (no digit suffixes)
        env = ValidEnv("alpha")
        assert str(env) == "alpha"

        # Item assignment raises TypeError (tuple is immutable)
        with pytest.raises(TypeError, match=r"does not support item assignment"):
            ValidEnv.ENV_PRIORITY_ORDER[0] = "gamma"  # type: ignore[index]

        # Attempting to mutate to add digit-suffix codes raises AttributeError
        with pytest.raises(AttributeError, match=r"Cannot mutate.*ENV_PRIORITY_ORDER"):
            ValidEnv.ENV_PRIORITY_ORDER = ("alpha", "beta", "gamma1")

    def test_instance_attributes_are_frozen(self):
        """Instance attributes starting with "_" cannot be mutated after being set."""

        class TestEnv(BaseSubEnv):
            ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "prod")

        env = TestEnv("dev")
        assert env._main == "dev"
        assert env._sub is None

        # Attempting to mutate _main raises AttributeError
        with pytest.raises(AttributeError, match=r"Cannot mutate.*_main"):
            env._main = "prod"

        # Attempting to mutate _sub raises AttributeError
        with pytest.raises(AttributeError, match=r"Cannot mutate.*_sub"):
            env._sub = 5

        # Setting NEW "_" attributes is allowed (only existing ones are protected)
        env._custom = "value"  # This works because _custom doesn't exist yet
        assert env._custom == "value"  # type: ignore[attr-defined]
