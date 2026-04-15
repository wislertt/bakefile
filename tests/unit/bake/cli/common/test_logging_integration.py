"""Integration tests for CLI verbosity + bakebook logging configuration.

Tests the full pipeline: params -> BakefileObject/Bakebook -> BakeSettings -> logging -> stderr.

Key concepts:
- bake_log: per-module filter (what modules emit)
- bake_log_verbosity: global minimum log level floor (what you actually see)
- Verbosity floor overrides per-module config
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from bake import Bakebook
from bake.cli.common.obj import BakefileObject
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from bake.utils.settings import BakeSettings


def _make_obj(
    bake_log: str = "debug",
    bake_log_verbosity: int = 0,
    bakebook: Bakebook | None = None,
) -> BakefileObject:
    return BakefileObject(
        chdir=Path("."),
        file_name=DEFAULT_FILE_NAME,
        bakebook_name=DEFAULT_BAKEBOOK_NAME,
        bake_log=bake_log,
        bake_log_verbosity=bake_log_verbosity,
        bake_log_pretty=False,
        bakebook=bakebook,
    )


class TestVerbosityFloorBehavior:
    """Test that verbosity controls the global minimum log level (floor).

    Verbosity maps to global_min_log_level:
    - 0 -> CRITICAL+1 (silent)
    - 1 -> WARNING (-v)
    - 2 -> INFO (-vv)
    - 3 -> DEBUG (-vvv)

    The floor overrides per-module config.
    """

    @pytest.mark.parametrize(
        "verbosity,visible_levels,hidden_levels",
        [
            (0, [], [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]),
            (1, [logging.WARNING, logging.ERROR], [logging.DEBUG, logging.INFO]),
            (2, [logging.INFO, logging.WARNING, logging.ERROR], [logging.DEBUG]),
            (3, [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR], []),
        ],
        ids=["silent", "warning", "info", "debug"],
    )
    def test_verbosity_floor(
        self,
        capsys: pytest.CaptureFixture[str],
        verbosity: int,
        visible_levels: list[int],
        hidden_levels: list[int],
    ) -> None:
        obj = _make_obj(bake_log="debug", bake_log_verbosity=verbosity)
        obj.setup_logging()

        logger = logging.getLogger(f"test_verbosity_floor_{verbosity}")
        messages = {
            logging.DEBUG: "debug msg",
            logging.INFO: "info msg",
            logging.WARNING: "warning msg",
            logging.ERROR: "error msg",
        }

        for level, msg in messages.items():
            logger.log(level, msg)

        captured = capsys.readouterr()

        for level in visible_levels:
            assert messages[level] in captured.err, (
                f"verbosity={verbosity}: {logging.getLevelName(level)} should be visible"
            )
        for level in hidden_levels:
            assert messages[level] not in captured.err, (
                f"verbosity={verbosity}: {logging.getLevelName(level)} should be hidden"
            )


class TestPerModuleWithVerbosityFloor:
    """Test that per-module config interacts correctly with verbosity floor."""

    def test_per_module_debug_blocked_by_floor(self, capsys: pytest.CaptureFixture[str]) -> None:
        """myapp=debug is blocked when verbosity floor is WARNING."""
        obj = _make_obj(bake_log="warning,myapp=debug", bake_log_verbosity=1)
        obj.setup_logging()

        logging.getLogger("myapp.blocked").debug("myapp debug blocked")
        logging.getLogger("other").warning("other warning passes")

        captured = capsys.readouterr()
        assert "myapp debug blocked" not in captured.err
        assert "other warning passes" in captured.err

    def test_per_module_debug_allowed_at_vvv(self, capsys: pytest.CaptureFixture[str]) -> None:
        """myapp=debug passes when verbosity floor is DEBUG (-vvv)."""
        obj = _make_obj(bake_log="warning,myapp=debug", bake_log_verbosity=3)
        obj.setup_logging()

        logging.getLogger("myapp.allowed").debug("myapp debug allowed")
        logging.getLogger("other").debug("other debug blocked by filter")
        logging.getLogger("other").warning("other warning passes")

        captured = capsys.readouterr()
        assert "myapp debug allowed" in captured.err
        assert "other debug blocked by filter" not in captured.err
        assert "other warning passes" in captured.err


class TestBakebookConfigIntegration:
    """Test that Bakebook config integrates with BakefileObject verbosity."""

    def test_bakefile_object_uses_bakebook_bake_log(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """BakefileObject.setup_logging() uses bakebook's bake_log when bakebook exists."""
        bb = Bakebook(bake_log="warning,bake=debug", bake_log_verbosity=0)
        obj = _make_obj(bake_log_verbosity=3, bakebook=bb)
        obj.setup_logging()

        logging.getLogger("bake.integration").debug("bake debug from bakebook")
        logging.getLogger("other").debug("other debug blocked")
        logging.getLogger("other").warning("other warning passes")

        captured = capsys.readouterr()
        assert "bake debug from bakebook" in captured.err
        assert "other debug blocked" not in captured.err
        assert "other warning passes" in captured.err

    def test_cli_verbosity_overrides_bakebook_verbosity(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """BakefileObject verbosity (from CLI) takes precedence over bakebook's."""
        bb = Bakebook(bake_log="debug", bake_log_verbosity=3)
        obj = _make_obj(bake_log_verbosity=1, bakebook=bb)
        obj.setup_logging()

        logging.getLogger("test").debug("debug suppressed by CLI verbosity")
        logging.getLogger("test").warning("warning passes")

        captured = capsys.readouterr()
        assert "debug suppressed by CLI verbosity" not in captured.err
        assert "warning passes" in captured.err

    def test_bakebook_setup_logging_non_cli_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Bakebook.setup_logging() works independently (non-CLI path)."""
        fresh_settings = BakeSettings()
        with patch("bake.bakebook.bakebook.bake_settings", fresh_settings):
            bb = Bakebook(bake_log="info,custom=debug", bake_log_verbosity=3)
            bb.setup_logging()

            logging.getLogger("custom.module").debug("custom debug appears")
            logging.getLogger("other").debug("other debug hidden")
            logging.getLogger("other").info("other info appears")

            captured = capsys.readouterr()

        assert "custom debug appears" in captured.err
        assert "other debug hidden" not in captured.err
        assert "other info appears" in captured.err
