"""Unit tests for environment presets."""

import pytest

from bakelib.environ import BaseEnv, GcpLandingZoneEnv


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
            match=r"Invalid GcpLandingZoneEnv: 'invalid'. Must be one of:",
        ):
            GcpLandingZoneEnv("invalid")

    @pytest.mark.parametrize(
        "higher,lower",
        [
            ("d", "n"),  # dev < nonprod
            ("n", "p"),  # nonprod < prod
            ("d", "s"),  # dev < shared
            ("b", "c"),  # alphabetical within shared
            ("c", "net"),
            ("net", "p"),
            ("p", "s"),
        ],
    )
    def test_priority_ordering(self, higher, lower):
        """Higher priority environment is less than lower priority."""
        assert GcpLandingZoneEnv(higher) < GcpLandingZoneEnv(lower)

    def test_full_comparison_chain(self):
        """Full comparison chain: d < n < b < c < net < p < s"""
        assert (
            GcpLandingZoneEnv("d")
            < GcpLandingZoneEnv("n")
            < GcpLandingZoneEnv("b")
            < GcpLandingZoneEnv("c")
            < GcpLandingZoneEnv("net")
            < GcpLandingZoneEnv("p")
            < GcpLandingZoneEnv("s")
        )

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
