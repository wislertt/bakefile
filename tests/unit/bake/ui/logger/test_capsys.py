import json
import logging
import sys

import loguru
import pytest
from _pytest.capture import CaptureResult

from bake.ui.logger import (
    UNPARSABLE_LINE,
    capsys_to_logs,
    capsys_to_logs_pretty,
    capture_to_logs,
    capture_to_logs_pretty,
    count_message_in_logs,
    find_log,
    has_message_in_logs,
    has_messages_in_logs,
    parse_pretty_log,
    setup_logging,
)
from bake.ui.logger.utils import LogKey
from tests.unit.bake.ui.logger.utils import has_required_keys


def test_capsys_to_logs(capsys: pytest.CaptureFixture[str]) -> None:
    """Test capsys_to_logs with JSON log format."""
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


def test_capsys_to_logs_pretty(capsys: pytest.CaptureFixture[str]) -> None:
    """Test capsys_to_logs_pretty with pretty log format."""
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


def test_capture_to_logs_preserve_unparsable_with_invalid_json() -> None:
    """Test capture_to_logs with preserve_unparsable=True and JSON missing required keys."""
    # Add a valid log with required keys
    valid_log = {
        LogKey.TIMESTAMP.value: "2024-01-01 00:00:00.000 +00:00",
        LogKey.LEVEL.value: "INFO",
        LogKey.NAME.value: "test",
        LogKey.MESSAGE.value: "valid message",
        LogKey.FUNCTION_NAME.value: "test_func",
        LogKey.LINE_NO.value: 1,
        LogKey.MODULE.value: "test",
        LogKey.PROCESS_NAME.value: "MainProcess",
        LogKey.FILE_NAME.value: "test.py",
        LogKey.THREAD_NAME.value: "MainThread",
    }
    err = '{"level": "INFO", "message": "test"}\nvalid_log_line\n' + json.dumps(valid_log) + "\n"

    capture = CaptureResult(out="", err=err)

    result = capture_to_logs(capture, preserve_unparsable=True)

    # Should include the unparsable invalid JSON, unparsable line, and the valid log
    assert len(result) == 3
    assert result[0] == {UNPARSABLE_LINE: '{"level": "INFO", "message": "test"}'}
    assert result[1] == {UNPARSABLE_LINE: "valid_log_line"}
    assert has_required_keys(result[2])


def test_parse_pretty_log_with_malformed_json_in_extra() -> None:
    """Test parse_pretty_log with malformed JSON in extra fields."""
    # Create a pretty log line with malformed JSON in extra field
    pretty_log = (
        "2024-01-01 00:00:00.000 +00:00 | INFO   | test.module:test_func:1 - test message - "
        "{not valid json} - "
        '{"process_name": "MainProcess", "file_name": "test.py", "thread_name": "MainThread"}'
    )

    result = parse_pretty_log(pretty_log)

    # Should parse successfully with unparsed extra field
    assert len(result) == 1
    assert result[0][LogKey.MESSAGE.value] == "test message"
    assert "_unparsed_extra" in result[0]
    assert result[0]["_unparsed_extra"] == "{not valid json}"
    assert result[0][LogKey.PROCESS_NAME.value] == "MainProcess"


def test_has_message_in_logs() -> None:
    """Test has_message_in_logs function."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
        {LogKey.MESSAGE.value: "third message"},
    ]

    assert has_message_in_logs(logs, "first")
    assert has_message_in_logs(logs, "second")
    assert has_message_in_logs(logs, "third")
    assert not has_message_in_logs(logs, "nonexistent")
    assert has_message_in_logs(logs, "message")  # regex match


def test_has_messages_in_logs_empty_messages() -> None:
    """Test has_messages_in_logs with empty messages list."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
    ]

    # Empty messages list should return True
    assert has_messages_in_logs(logs, [])


def test_has_messages_in_logs_not_all_found() -> None:
    """Test has_messages_in_logs when not all messages are found in order."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
        {LogKey.MESSAGE.value: "third message"},
    ]

    # Messages not in order should return False
    assert not has_messages_in_logs(logs, ["third", "first"])
    assert not has_messages_in_logs(logs, ["first", "nonexistent"])


def test_has_messages_in_logs_success() -> None:
    """Test has_messages_in_logs when all messages are found in order."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
        {LogKey.MESSAGE.value: "third message"},
    ]

    # Messages in order should return True
    assert has_messages_in_logs(logs, ["first", "second"])
    assert has_messages_in_logs(logs, ["first", "second", "third"])


def test_find_log_with_index() -> None:
    """Test find_log function with index parameter."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
        {LogKey.MESSAGE.value: "third message"},
        {LogKey.MESSAGE.value: "first message again"},
    ]

    # Find first occurrence
    assert find_log(logs, "first")[LogKey.MESSAGE.value] == "first message"

    # Find second occurrence (index=1)
    assert find_log(logs, "first", index=1)[LogKey.MESSAGE.value] == "first message again"

    # Find with regex pattern
    assert find_log(logs, "second")[LogKey.MESSAGE.value] == "second message"


def test_capture_to_logs_pretty_with_empty_output() -> None:
    """Test capture_to_logs_pretty with empty output."""
    capture = CaptureResult(out="", err="")

    result = capture_to_logs_pretty(capture)

    assert result == []


def test_capture_to_logs_pretty_with_whitespace_only() -> None:
    """Test capture_to_logs_pretty with whitespace-only output."""
    capture = CaptureResult(out="", err="   \n\n  \t  ")

    result = capture_to_logs_pretty(capture)

    assert result == []


def test_count_message_in_logs() -> None:
    """Test count_message_in_logs function."""
    logs = [
        {LogKey.MESSAGE.value: "first message"},
        {LogKey.MESSAGE.value: "second message"},
        {LogKey.MESSAGE.value: "first message again"},
        {LogKey.MESSAGE.value: "third message"},
    ]

    assert count_message_in_logs(logs, "first") == 2
    assert count_message_in_logs(logs, "second") == 1
    assert count_message_in_logs(logs, "third") == 1
    assert count_message_in_logs(logs, "nonexistent") == 0
    assert count_message_in_logs(logs, "message") == 4  # regex match all
