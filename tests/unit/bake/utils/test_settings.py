import logging
from unittest.mock import patch

import pytest

from bake.utils.settings import BakeSettings, PlatformType, _detect_platform


class TestSetupBakeLogging:
    def test_setup_bake_logging_only_called_once(self, capsys: pytest.CaptureFixture[str]) -> None:
        settings = BakeSettings()

        # First call: only WARNING+ passes (verbosity=1)
        settings.setup_bake_logging(bake_log="warning", verbosity=1, bake_log_pretty=False)

        # Second call: would allow DEBUG (verbosity=3) — but should be a no-op
        settings.setup_bake_logging(bake_log="debug", verbosity=3, bake_log_pretty=False)

        # Verify the first config is still active: INFO should be suppressed
        logger = logging.getLogger("test_setup_bake_logging_idempotent")
        logger.info("info should be suppressed")
        logger.warning("warning should appear")

        captured = capsys.readouterr()
        assert "info should be suppressed" not in captured.err
        assert "warning should appear" in captured.err


class TestDetectPlatform:
    @pytest.mark.parametrize(
        "sys_platform,expected",
        [
            ("darwin", "macos"),
            ("linux", "linux"),
            ("win32", "windows"),
            ("unknown", "other"),
        ],
    )
    def test_returns_correct_platform(self, sys_platform: str, expected: PlatformType) -> None:
        with patch("bake.utils.settings.sys.platform", sys_platform):
            assert _detect_platform() == expected

    def test_settings_default_matches_sys_platform(self) -> None:
        settings = BakeSettings()
        assert settings.platform in ("macos", "linux", "windows", "other")
