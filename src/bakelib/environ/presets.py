"""Preset environment configurations.

This module contains pre-configured environment classes for common use cases.
Users can also create their own environments by inheriting from BaseEnv.
"""

from typing import ClassVar

from bakelib.environ.base import BaseEnv


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

    ENV_ORDER: ClassVar[list[str | set[str]]] = [
        "d",
        "n",
        {"p", "s", "b", "c", "net"},
    ]

    def is_shared(self) -> bool:
        return self.code in {"s", "b", "c", "net"}

    @property
    def name(self) -> str:
        names = {
            "d": "Development",
            "n": "Nonproduction",
            "p": "Production",
            "s": "Shared",
            "b": "Bootstrap",
            "c": "Common",
            "net": "Network",
        }
        return names[self.code]

    @property
    def code(self) -> str:
        return str(self)

    @property
    def secondary_name(self) -> str:
        return self.name if not self.is_shared() else "Shared"

    @property
    def secondary_code(self) -> str:
        return self.code if not self.is_shared() else "s"
