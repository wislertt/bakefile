"""Tests for bakefile.ui.logger.capsys module."""

import logging
import sys

import loguru
import pytest

from bake.ui.logger import UNPARSABLE_LINE, capsys_to_logs, capsys_to_logs_pretty, setup_logging
from tests.bake.ui.logger.utils import has_required_keys


def test_capsys_to_logs(reset_all_logger_state: None, capsys: pytest.CaptureFixture[str]) -> None:
    """Test capsys_to_logs with JSON log format."""
    _ = reset_all_logger_state

    setup_logging(
        level_per_module={"": logging.INFO}, thread_local_context=None, is_pretty_log=False
    )

    # Write unparsable line to stderr
    sys.stderr.write("This is not a JSON line\n")

    # Write incomplete JSON (missing required keys)
    sys.stderr.write('{"level": "INFO", "message": "test"}\n')

    # Write empty lines
    sys.stderr.write("\n\n")

    # Log valid messages
    loguru.logger.info("test_info_1")
    loguru.logger.warning("test_warning_1")

    try:
        raise RuntimeError("test_error")
    except RuntimeError:
        loguru.logger.exception("test_exception")

    loguru.logger.info("test_info_2")

    # Test without preserve_unparsable - should only return valid logs
    parsed_logs = capsys_to_logs(capsys)

    # Basic structure checks
    assert len(parsed_logs) == 4
    assert all(has_required_keys(log) for log in parsed_logs)

    # Message content checks
    messages = [log["message"] for log in parsed_logs]
    assert any("test_info_1" in msg for msg in messages)
    assert any("test_warning_1" in msg for msg in messages)
    assert any("test_exception" in msg for msg in messages)
    assert any("test_info_2" in msg for msg in messages)

    # Exception info checks
    exc_log = next(log for log in parsed_logs if "test_exception" in log["message"])
    assert "exc_info" in exc_log
    assert "Traceback" in exc_log["exc_info"]
    assert "RuntimeError" in exc_log["exc_info"]
    assert "test_error" in exc_log["exc_info"]

    # Test with preserve_unparsable=True - should return all lines
    sys.stderr.write("unparsable_line_2\n")
    loguru.logger.info("test_info_3")
    parsed_logs_with_unparsable = capsys_to_logs(capsys, preserve_unparsable=True)

    assert len(parsed_logs_with_unparsable) == 2
    assert parsed_logs_with_unparsable[0] == {UNPARSABLE_LINE: "unparsable_line_2"}
    assert has_required_keys(parsed_logs_with_unparsable[1])


def test_capsys_to_logs_pretty(
    reset_all_logger_state: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test capsys_to_logs_pretty with pretty log format."""
    _ = reset_all_logger_state

    setup_logging(
        level_per_module={"": logging.INFO}, thread_local_context=None, is_pretty_log=True
    )

    # Log messages in pretty format
    loguru.logger.info("test_info_1")
    loguru.logger.warning("test_warning_1")

    try:
        raise RuntimeError("test_error")
    except RuntimeError:
        loguru.logger.exception("test_exception")

    loguru.logger.info("test_info_2")
    loguru.logger.warning("test_warning_2")

    parsed_logs = capsys_to_logs_pretty(capsys)

    # Basic structure checks
    assert len(parsed_logs) == 5
    assert all(has_required_keys(log) for log in parsed_logs)

    # Message content checks
    messages = [log["message"] for log in parsed_logs]
    assert any("test_info_1" in msg for msg in messages)
    assert any("test_warning_1" in msg for msg in messages)
    assert any("test_exception" in msg for msg in messages)
    assert any("test_info_2" in msg for msg in messages)
    assert any("test_warning_2" in msg for msg in messages)

    # Exception info checks
    assert "exc_info" in parsed_logs[2]
    assert "Traceback" in parsed_logs[2]["exc_info"]
    assert "RuntimeError" in parsed_logs[2]["exc_info"]
    assert "test_error" in parsed_logs[2]["exc_info"]
