"""Unit tests for environment presets."""

import pytest
from pydantic import BaseModel, ValidationError

from bakelib.environ.base import BaseEnv
from bakelib.environ.presets import GcpLandingZoneEnv, GcpLandingZoneSubEnv


class TestGcpLandingZoneEnv:
    """Test GcpLandingZoneEnv preset."""

    @pytest.mark.parametrize(
        "code",
        ["d", "n", "p", "s", "b", "c", "net"],
    )
    def test_create_valid_env(self, code):
        """Can create valid environment from code."""
        env = GcpLandingZoneEnv(code)
        assert str(env) == code
        assert isinstance(env, BaseEnv)

    def test_create_invalid_env_raises_error(self):
        """Invalid environment code raises ValueError."""
        with pytest.raises(
            ValueError,
            match=r"Value 'invalid' not found in ENV_PRIORITY_ORDER\. Must be one of:",
        ):
            GcpLandingZoneEnv("invalid")

    @pytest.mark.parametrize(
        "higher,lower",
        [
            ("d", "n"),  # dev < nonprod
            ("n", "p"),  # nonprod < prod
            ("d", "s"),  # dev < shared
            # Note: b, c, net, p, s are all in the same priority set
            # They are equal for ordering, not alphabetically ordered
        ],
    )
    def test_priority_ordering(self, higher, lower):
        """Higher priority environment is less than lower priority."""
        assert GcpLandingZoneEnv(higher) < GcpLandingZoneEnv(lower)

    def test_full_comparison_chain(self):
        """Comparison chain: d < n < {p, s, b, c, net} (equal priority group)"""
        assert GcpLandingZoneEnv("d") < GcpLandingZoneEnv("n")
        # All of p, s, b, c, net have equal priority
        shared = GcpLandingZoneEnv("p")
        assert not (shared < GcpLandingZoneEnv("s"))
        assert not (shared < GcpLandingZoneEnv("b"))
        assert not (shared < GcpLandingZoneEnv("c"))
        assert not (shared < GcpLandingZoneEnv("net"))
        # But they're <= and >= each other
        assert shared <= GcpLandingZoneEnv("s")
        assert shared >= GcpLandingZoneEnv("s")

    def test_equal_priority_items_are_equal(self):
        """Items in same priority set are equal."""
        c = GcpLandingZoneEnv("c")
        net = GcpLandingZoneEnv("net")
        # Same priority = equal
        assert c == net
        assert not (c < net)
        assert not (net < c)
        # And they're <= and >= each other
        assert c <= net
        assert c >= net
        # But different string values
        assert str(c) != str(net)

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("s", True),
            ("b", True),
            ("c", True),
            ("net", True),
            ("d", False),
            ("n", False),
            ("p", False),
        ],
    )
    def test_is_shared(self, code, expected):
        """is_shared returns correct value for each environment."""
        assert GcpLandingZoneEnv(code).is_shared() is expected

    def test_repr_and_inheritance(self):
        """Test repr and inheritance."""
        env = GcpLandingZoneEnv("d")
        assert repr(env) == "GcpLandingZoneEnv('d')"
        assert isinstance(env, BaseEnv)
        assert issubclass(GcpLandingZoneEnv, BaseEnv)

    @pytest.mark.parametrize(
        "code,expected_name",
        [
            ("d", "Development"),
            ("n", "Nonproduction"),
            ("p", "Production"),
            ("s", "Shared"),
            ("b", "Bootstrap"),
            ("c", "Common"),
            ("net", "Network"),
        ],
    )
    def test_name_property(self, code, expected_name):
        """name property returns full name for environment code."""
        assert GcpLandingZoneEnv(code).name == expected_name

    @pytest.mark.parametrize(
        "code,expected_secondary",
        [
            ("d", "Development"),
            ("n", "Nonproduction"),
            ("p", "Production"),
            ("s", "Shared"),
            ("b", "Shared"),
            ("c", "Shared"),
            ("net", "Shared"),
        ],
    )
    def test_secondary_name_property(self, code, expected_secondary):
        """secondary_name property returns correct secondary name."""
        assert GcpLandingZoneEnv(code).secondary_name == expected_secondary

    @pytest.mark.parametrize(
        "code,expected_secondary_code",
        [
            ("d", "d"),
            ("n", "n"),
            ("p", "p"),
            ("s", "s"),
            ("b", "s"),
            ("c", "s"),
            ("net", "s"),
        ],
    )
    def test_secondary_code_property(self, code, expected_secondary_code):
        """secondary_code property returns 's' for shared tier, otherwise original code."""
        assert GcpLandingZoneEnv(code).secondary_code == expected_secondary_code

    @pytest.mark.parametrize(
        "code,expected_code",
        [
            ("d", "d"),
            ("n", "n"),
            ("p", "p"),
            ("s", "s"),
            ("b", "b"),
            ("c", "c"),
            ("net", "net"),
        ],
    )
    def test_code_property(self, code, expected_code):
        """code property returns the environment code string."""
        assert GcpLandingZoneEnv(code).code == expected_code


class TestGcpLandingZoneSubEnvCreation:
    def test_create_valid_base_envs(self):
        """All valid base codes can be created."""
        valid_codes = ["d", "n", "p", "s", "b", "c", "net"]

        for code in valid_codes:
            env = GcpLandingZoneSubEnv(code)
            assert str(env) == code

    def test_create_valid_sub_envs(self):
        """All valid sub-codes can be created."""
        valid_sub_codes = ["d1", "d2", "d99", "n1", "n2", "net1", "net2", "p1", "s1"]

        for code in valid_sub_codes:
            env = GcpLandingZoneSubEnv(code)
            assert str(env) == code

    def test_invalid_code_raises_error(self):
        """Invalid codes raise ValueError."""
        invalid_codes = ["x", "x1", "d0", "net0"]

        for code in invalid_codes:
            with pytest.raises(ValueError):
                GcpLandingZoneSubEnv(code)


class TestGcpLandingZoneSubEnvInheritedProperties:
    def test_inherited_name_property_base_envs(self):
        """name property works for base envs."""
        assert GcpLandingZoneSubEnv("d").name == "Development"
        assert GcpLandingZoneSubEnv("n").name == "Nonproduction"
        assert GcpLandingZoneSubEnv("p").name == "Production"
        assert GcpLandingZoneSubEnv("s").name == "Shared"
        assert GcpLandingZoneSubEnv("b").name == "Bootstrap"
        assert GcpLandingZoneSubEnv("c").name == "Common"
        assert GcpLandingZoneSubEnv("net").name == "Network"

    def test_inherited_name_property_sub_envs(self):
        """name property includes sub-number for sub-envs."""
        assert GcpLandingZoneSubEnv("d1").name == "Development1"
        assert GcpLandingZoneSubEnv("d99").name == "Development99"
        assert GcpLandingZoneSubEnv("n1").name == "Nonproduction1"
        assert GcpLandingZoneSubEnv("net1").name == "Network1"

    def test_inherited_is_shared_property(self):
        """is_shared() works for both base and sub-envs."""
        # Not shared
        assert not GcpLandingZoneSubEnv("d").is_shared()
        assert not GcpLandingZoneSubEnv("d1").is_shared()
        assert not GcpLandingZoneSubEnv("n").is_shared()
        assert not GcpLandingZoneSubEnv("p").is_shared()

        # Shared
        assert GcpLandingZoneSubEnv("s").is_shared()
        assert GcpLandingZoneSubEnv("s1").is_shared()
        assert GcpLandingZoneSubEnv("b").is_shared()
        assert GcpLandingZoneSubEnv("b1").is_shared()
        assert GcpLandingZoneSubEnv("c").is_shared()
        assert GcpLandingZoneSubEnv("net").is_shared()
        assert GcpLandingZoneSubEnv("net1").is_shared()

    def test_inherited_code_property(self):
        """code property returns full code string."""
        assert GcpLandingZoneSubEnv("d").code == "d"
        assert GcpLandingZoneSubEnv("d1").code == "d1"
        assert GcpLandingZoneSubEnv("net1").code == "net1"

    def test_inherited_secondary_name_property(self):
        """secondary_name property works correctly."""
        assert GcpLandingZoneSubEnv("d").secondary_name == "Development"
        assert GcpLandingZoneSubEnv("d1").secondary_name == "Development1"
        assert GcpLandingZoneSubEnv("s").secondary_name == "Shared"
        assert GcpLandingZoneSubEnv("s1").secondary_name == "Shared1"
        assert GcpLandingZoneSubEnv("net1").secondary_name == "Shared1"

    def test_inherited_secondary_code_property(self):
        """secondary_code property returns 's' for shared envs, with sub-number for sub-envs."""
        assert GcpLandingZoneSubEnv("d").secondary_code == "d"
        assert GcpLandingZoneSubEnv("d1").secondary_code == "d1"
        assert GcpLandingZoneSubEnv("s").secondary_code == "s"
        assert GcpLandingZoneSubEnv("s1").secondary_code == "s1"
        assert GcpLandingZoneSubEnv("net1").secondary_code == "s1"

    def test_inherited_secondary_main_name_property(self):
        """secondary_main_name property returns main name (no sub-number)."""
        # Non-shared: returns actual main name
        assert GcpLandingZoneSubEnv("d").secondary_main_name == "Development"
        assert GcpLandingZoneSubEnv("d1").secondary_main_name == "Development"
        assert GcpLandingZoneSubEnv("n99").secondary_main_name == "Nonproduction"

        # Shared: returns "Shared"
        assert GcpLandingZoneSubEnv("s").secondary_main_name == "Shared"
        assert GcpLandingZoneSubEnv("s1").secondary_main_name == "Shared"
        assert GcpLandingZoneSubEnv("b").secondary_main_name == "Shared"
        assert GcpLandingZoneSubEnv("net1").secondary_main_name == "Shared"

    def test_inherited_secondary_main_code_property(self):
        """secondary_main_code property returns main code (no sub-number)."""
        # Non-shared: returns actual main code
        assert GcpLandingZoneSubEnv("d").secondary_main_code == "d"
        assert GcpLandingZoneSubEnv("d1").secondary_main_code == "d"
        assert GcpLandingZoneSubEnv("n99").secondary_main_code == "n"

        # Shared: returns "s"
        assert GcpLandingZoneSubEnv("s").secondary_main_code == "s"
        assert GcpLandingZoneSubEnv("s1").secondary_main_code == "s"
        assert GcpLandingZoneSubEnv("b").secondary_main_code == "s"
        assert GcpLandingZoneSubEnv("net1").secondary_main_code == "s"


class TestGcpLandingZoneSubEnvComparison:
    def test_dev_tier_comparison(self):
        """Development tier: d2 < d1 < d (higher sub applies first, no-sub applies last)."""
        d = GcpLandingZoneSubEnv("d")
        d1 = GcpLandingZoneSubEnv("d1")
        d2 = GcpLandingZoneSubEnv("d2")

        assert d2 < d1
        assert d1 < d
        assert d2 < d

    def test_nonprod_tier_comparison(self):
        """Nonprod tier: n2 < n1 < n (higher sub applies first, no-sub applies last)."""
        n = GcpLandingZoneSubEnv("n")
        n1 = GcpLandingZoneSubEnv("n1")
        n2 = GcpLandingZoneSubEnv("n2")

        assert n2 < n1
        assert n1 < n
        assert n2 < n

    def test_network_tier_comparison(self):
        """Network tier: net2 < net1 < net (higher sub applies first, no-sub applies last)."""
        net = GcpLandingZoneSubEnv("net")
        net1 = GcpLandingZoneSubEnv("net1")
        net2 = GcpLandingZoneSubEnv("net2")

        assert net2 < net1
        assert net1 < net
        assert net2 < net

    def test_cross_tier_comparison(self):
        """Cross-tier: d < n < p (lower index applies first)."""
        d = GcpLandingZoneSubEnv("d")
        d99 = GcpLandingZoneSubEnv("d99")
        n = GcpLandingZoneSubEnv("n")
        n1 = GcpLandingZoneSubEnv("n1")
        p = GcpLandingZoneSubEnv("p")

        assert d < n
        assert d < n1
        assert d99 < p
        assert n1 < p

    def test_full_comparison_chain(self):
        """Full chain: d2 < d1 < d < n2 < n1 < n < p."""
        assert GcpLandingZoneSubEnv("d2") < GcpLandingZoneSubEnv("d1")
        assert GcpLandingZoneSubEnv("d1") < GcpLandingZoneSubEnv("d")
        assert GcpLandingZoneSubEnv("d") < GcpLandingZoneSubEnv("n2")
        assert GcpLandingZoneSubEnv("n2") < GcpLandingZoneSubEnv("n1")
        assert GcpLandingZoneSubEnv("n1") < GcpLandingZoneSubEnv("n")
        assert GcpLandingZoneSubEnv("n") < GcpLandingZoneSubEnv("p")

    def test_docstring_comparison_chain(self):
        """Test comparison chain as documented in docstring.

        Comparison order (lower = applies first):
        - d3 < d2 < d1 < d < n3 < n2 < n1 < n
        - n < (p3 == s3 == b3 == c3 == net3) < s2
        - s3 < (p2 == s2 == b2 == c2 == net2) < s1
        - s2 < (p1 == s1 == b1 == c1 == net1) < s
        - s1 < (p == s == b == c == net)
        """
        # Create vars for readability
        d3 = GcpLandingZoneSubEnv("d3")
        d2 = GcpLandingZoneSubEnv("d2")
        d1 = GcpLandingZoneSubEnv("d1")
        d = GcpLandingZoneSubEnv("d")

        n3 = GcpLandingZoneSubEnv("n3")
        n2 = GcpLandingZoneSubEnv("n2")
        n1 = GcpLandingZoneSubEnv("n1")
        n = GcpLandingZoneSubEnv("n")

        p3 = GcpLandingZoneSubEnv("p3")
        s3 = GcpLandingZoneSubEnv("s3")
        b3 = GcpLandingZoneSubEnv("b3")
        c3 = GcpLandingZoneSubEnv("c3")
        net3 = GcpLandingZoneSubEnv("net3")

        p2 = GcpLandingZoneSubEnv("p2")
        s2 = GcpLandingZoneSubEnv("s2")
        b2 = GcpLandingZoneSubEnv("b2")
        c2 = GcpLandingZoneSubEnv("c2")
        net2 = GcpLandingZoneSubEnv("net2")

        p1 = GcpLandingZoneSubEnv("p1")
        s1 = GcpLandingZoneSubEnv("s1")
        b1 = GcpLandingZoneSubEnv("b1")
        c1 = GcpLandingZoneSubEnv("c1")
        net1 = GcpLandingZoneSubEnv("net1")

        p = GcpLandingZoneSubEnv("p")
        s = GcpLandingZoneSubEnv("s")
        b = GcpLandingZoneSubEnv("b")
        c = GcpLandingZoneSubEnv("c")
        net = GcpLandingZoneSubEnv("net")

        # d3 < d2 < d1 < d < n3 < n2 < n1 < n
        assert d3 < d2 < d1 < d < n3 < n2 < n1 < n

        # Verify equal priority within shared-tier sub-groups (s, b, c, net) and production (p)
        assert p3 == s3 == b3 == c3 == net3
        assert p2 == s2 == b2 == c2 == net2
        assert p1 == s1 == b1 == c1 == net1
        assert p == s == b == c == net

        # Cross-tier ordering (shared-tier and production have equal priority):
        assert n < s3 < s2 < s1 < s  # using s as shared-tier rep
        assert n < p3 < p2 < p1 < p  # using p as production

    def test_equality_within_tier(self):
        """Different sub numbers are not equal."""
        d1 = GcpLandingZoneSubEnv("d1")
        d2 = GcpLandingZoneSubEnv("d2")

        assert d1 != d2

    def test_equality_same_value(self):
        """Same value equals itself."""
        d1 = GcpLandingZoneSubEnv("d1")
        d1_copy = GcpLandingZoneSubEnv("d1")

        assert d1 == d1_copy

    def test_prod_tier_equal_priority(self):
        """All prod tier envs have equal priority (same index)."""
        p = GcpLandingZoneSubEnv("p")
        s = GcpLandingZoneSubEnv("s")
        b = GcpLandingZoneSubEnv("b")
        c = GcpLandingZoneSubEnv("c")
        net = GcpLandingZoneSubEnv("net")

        p1 = GcpLandingZoneSubEnv("p1")
        s1 = GcpLandingZoneSubEnv("s1")

        # All equal (same priority tier)
        assert p == s == b == c == net
        assert p1 == s1


class TestGcpLandingZoneSubEnvPydanticIntegration:
    """Test Pydantic v2 integration for GcpLandingZoneSubEnv."""

    def test_pydantic_model_with_sub_env_field(self):
        """Pydantic accepts GcpLandingZoneSubEnv."""

        class Model(BaseModel):
            env: GcpLandingZoneSubEnv

        m = Model(env="d1")  # ty: ignore[invalid-argument-type]
        assert isinstance(m.env, GcpLandingZoneSubEnv)
        assert str(m.env) == "d1"

    def test_pydantic_raises_error_for_invalid_value(self):
        """Pydantic raises ValidationError for invalid codes."""

        class Model(BaseModel):
            env: GcpLandingZoneSubEnv

        with pytest.raises(ValidationError):
            Model(env="x1")  # ty: ignore[invalid-argument-type]


class TestGcpLandingZoneSubEnvEdgeCases:
    def test_multi_digit_sub_numbers(self):
        """Multi-digit sub numbers: higher applies first (d100 < d99 < d10)."""
        d10 = GcpLandingZoneSubEnv("d10")
        d99 = GcpLandingZoneSubEnv("d99")
        d100 = GcpLandingZoneSubEnv("d100")

        assert d100 < d99
        assert d99 < d10

    def test_repr(self):
        """repr shows class name and value."""
        env = GcpLandingZoneSubEnv("d1")
        assert repr(env) == "GcpLandingZoneSubEnv('d1')"

    def test_str_behavior(self):
        """str() returns the code."""
        env = GcpLandingZoneSubEnv("net1")
        assert str(env) == "net1"
        assert isinstance(env, str)

    def test_is_subclass_of_base_env(self):
        """GcpLandingZoneSubEnv is a subclass of BaseEnv."""
        assert issubclass(GcpLandingZoneSubEnv, BaseEnv)
        assert isinstance(GcpLandingZoneSubEnv("d"), BaseEnv)


class TestGcpLandingZoneEnvFrozenClassVariables:
    """Test that CAPS class variables are frozen and cannot be mutated."""

    def test_env_priority_order_is_frozen(self):
        """ENV_PRIORITY_ORDER cannot be reassigned at class level."""
        with pytest.raises(AttributeError, match=r"Cannot mutate.*ENV_PRIORITY_ORDER.*frozen"):
            GcpLandingZoneEnv.ENV_PRIORITY_ORDER = ("x", "y")

    def test_names_is_frozen(self):
        """NAMES cannot be reassigned at class level."""
        with pytest.raises(AttributeError, match=r"Cannot mutate.*NAMES.*frozen"):
            GcpLandingZoneEnv.NAMES = {"x": "y"}  # ty: ignore[invalid-assignment]

    def test_names_dict_cannot_be_mutated(self):
        """NAMES dictionary content cannot be modified (MappingProxyType)."""
        with pytest.raises(TypeError, match=r"does not support item assignment"):
            GcpLandingZoneEnv.NAMES["d"] = "Hacked"  # ty: ignore[invalid-assignment]

    def test_shared_codes_is_frozen(self):
        """SHARED_CODES cannot be reassigned at class level."""
        with pytest.raises(AttributeError, match=r"Cannot mutate.*SHARED_CODES.*frozen"):
            GcpLandingZoneEnv.SHARED_CODES = frozenset()

    def test_shared_name_is_frozen(self):
        """SHARED_NAME cannot be reassigned at class level."""
        with pytest.raises(AttributeError, match=r"Cannot mutate.*SHARED_NAME.*frozen"):
            GcpLandingZoneEnv.SHARED_NAME = "New"

    def test_shared_code_is_frozen(self):
        """SHARED_CODE cannot be reassigned at class level."""
        with pytest.raises(AttributeError, match=r"Cannot mutate.*SHARED_CODE.*frozen"):
            GcpLandingZoneEnv.SHARED_CODE = "x"
