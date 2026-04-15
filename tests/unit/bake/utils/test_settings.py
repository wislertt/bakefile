import logging

import pytest

from bake.utils.settings import BakeSettings


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
