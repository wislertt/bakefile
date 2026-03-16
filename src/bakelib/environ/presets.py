"""Preset environment configurations.

This module contains pre-configured environment classes for common use cases.
Users can also create their own environments by inheriting from BaseEnv.
"""

from types import MappingProxyType
from typing import ClassVar

from bakelib.environ.base import BaseEnv, BaseSubEnv, EnvPriorityOrderType


class GcpLandingZoneEnv(BaseEnv):
    """GCP Landing Zone base environments.

    Environment codes follow GCP Security Foundations Blueprint conventions:
    https://docs.cloud.google.com/architecture/blueprints/security-foundations/summary

    Environment Codes:
    - d               - Development
    - n               - Nonproduction
    - p               - Production
    - s               - Shared
    - b               - Bootstrap
    - c               - Common
    - net             - Network

    Tiers (ordered by priority, lower index = higher priority):
    - d (development) - lowest priority
    - n (nonprod)
    - p/s/b/c/net     - highest priority, all equal (production + shared)

    Example:
        env = GcpLandingZoneEnv("d")
        assert env < GcpLandingZoneEnv("n")
        assert GcpLandingZoneEnv("n") < GcpLandingZoneEnv("p")
    """

    ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = (
        "d",
        "n",
        frozenset({"p", "s", "b", "c", "net"}),
    )

    NAMES: ClassVar[MappingProxyType[str, str]] = MappingProxyType(
        {
            "d": "Development",
            "n": "Nonproduction",
            "p": "Production",
            "s": "Shared",
            "b": "Bootstrap",
            "c": "Common",
            "net": "Network",
        }
    )

    SHARED_CODES: ClassVar[frozenset[str]] = frozenset({"s", "b", "c", "net"})
    SHARED_NAME: ClassVar[str] = "Shared"
    SHARED_CODE: ClassVar[str] = "s"

    def is_shared(self) -> bool:
        return self.code in self.SHARED_CODES

    @property
    def name(self) -> str:
        return self.NAMES[self.code]

    @property
    def code(self) -> str:
        return str(self)

    @property
    def secondary_name(self) -> str:
        return self.name if not self.is_shared() else self.SHARED_NAME

    @property
    def secondary_code(self) -> str:
        return self.code if not self.is_shared() else self.SHARED_CODE


class GcpLandingZoneSubEnv(GcpLandingZoneEnv, BaseSubEnv):
    """GCP Landing Zone environments with sub-environment support.

    Comparison order (lower = applies first):
    - d3 < d2 < d1 < d < n3 < n2 < n1 < n
    - Shared-tier (s, b, c, net) and production (p) have equal priority:
      p3 == s3 == b3 == c3 == net3
      p2 == s2 == b2 == c2 == net2
      p1 == s1 == b1 == c1 == net1
      p == s == b == c == net
    - Cross-tier: n < s3 < s2 < s1 < s and n < p3 < p2 < p1 < p

    Example:
        env = GcpLandingZoneSubEnv("d1")
        assert env < GcpLandingZoneSubEnv("d")
        assert env.name == "Development1"
    """

    def is_shared(self) -> bool:
        return self.main in self.SHARED_CODES

    @property
    def name(self) -> str:
        return f"{self.NAMES[self.main]}{self.sub or ''}"

    @property
    def secondary_main_name(self) -> str:
        return self.NAMES[self.main] if not self.is_shared() else self.SHARED_NAME

    @property
    def secondary_main_code(self) -> str:
        return self.main if not self.is_shared() else self.SHARED_CODE

    @property
    def secondary_name(self) -> str:
        return f"{self.secondary_main_name}{self.sub or ''}"

    @property
    def secondary_code(self) -> str:
        return f"{self.secondary_main_code}{self.sub or ''}"
