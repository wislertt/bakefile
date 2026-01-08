import json
import re
from typing import TYPE_CHECKING, Any

import orjson

from bake.ui.logger.utils import UNPARSABLE_LINE, LogKey, LogType

if TYPE_CHECKING:
    import _pytest.capture
    import pytest


def has_required_keys(log: LogType) -> bool:
    return LogKey.required_keys().issubset(log.keys())


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _safe_parse_dict_str(dict_str: str, unparsed_key: str = "_unparsed") -> dict[str, Any]:
    try:
        return orjson.loads(dict_str)
    except (TypeError, ValueError):
        # For malformed JSON, preserve original string for debugging
        return {unparsed_key: dict_str}


def parse_pretty_log(pretty_output: str) -> list[LogType]:
    """Parse pretty log format back into structured log entries."""
    # Strip ANSI codes first
    clean_output = strip_ansi(pretty_output)

    log_pattern = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} [+-]\d{2}:\d{2}) \| "
        r"(?P<level>\w+)\s+\| "
        r"(?P<name>[\w.]+):(?P<function>[\w_<>]+):(?P<line>\d+) - "
        r"(?P<message>.+?) - "
        r"(?P<extra>\{.*?\}) - "
        r"(?P<default_extra>\{.*?\})"
        r"(?:\n\n(?P<exception>Traceback[\s\S]*?))?(?=\n\n\d{4}-\d{2}-\d{2}|\n\d{4}-\d{2}-\d{2}|$)",
        re.DOTALL,
    )

    matches = log_pattern.findall(clean_output)
    parsed_logs = []
    for match in matches:
        # Unpack the match tuple (findall returns tuples, not match objects)
        timestamp, level, name, function, line, message, extra, default_extra, exception = match

        # Parse extra fields safely (handles non-literal values like PosixPath)
        extra_dict = _safe_parse_dict_str(extra, "_unparsed_extra")
        default_extra_dict = _safe_parse_dict_str(default_extra, "_unparsed_default_extra")

        log_data = {
            LogKey.TIMESTAMP.value: timestamp,
            LogKey.LEVEL.value: level,
            LogKey.NAME.value: name,
            LogKey.MODULE.value: name.split(".")[-1],
            LogKey.FUNCTION_NAME.value: function,
            LogKey.LINE_NO.value: int(line),
            LogKey.MESSAGE.value: message,
            **extra_dict,
            **default_extra_dict,
        }

        # Add exception if present
        if exception:
            log_data[LogKey.EXCEPTION.value] = exception

        # Map default_extra to LogKey fields
        if "process_name" in default_extra_dict:
            log_data[LogKey.PROCESS_NAME.value] = default_extra_dict["process_name"]
        if "file_name" in default_extra_dict:
            log_data[LogKey.FILE_NAME.value] = default_extra_dict["file_name"]
        if "thread_name" in default_extra_dict:
            log_data[LogKey.THREAD_NAME.value] = default_extra_dict["thread_name"]

        parsed_logs.append(log_data)

    return parsed_logs


def capture_to_logs(
    capture: "_pytest.capture.CaptureResult[str]", preserve_unparsable: bool = False
) -> list[LogType]:
    log_lines = capture.err.strip().split("\n")
    parsed_logs = []

    for line in log_lines:
        if not line:
            continue
        try:
            parsed_log = json.loads(line)
            if not has_required_keys(parsed_log):
                if preserve_unparsable:
                    parsed_logs.append({UNPARSABLE_LINE: line})
                continue
            parsed_logs.append(parsed_log)
        except json.JSONDecodeError:
            if preserve_unparsable:
                parsed_logs.append({UNPARSABLE_LINE: line})
            continue
    return parsed_logs


def capture_to_logs_pretty(capture: "_pytest.capture.CaptureResult[str]") -> list[LogType]:
    pretty_output = capture.err
    if not pretty_output.strip():
        return []
    return parse_pretty_log(pretty_output)


def capsys_to_logs(
    capsys: "pytest.CaptureFixture[str]", preserve_unparsable: bool = False
) -> list[LogType]:
    capture = capsys.readouterr()
    return capture_to_logs(capture=capture, preserve_unparsable=preserve_unparsable)


def capsys_to_logs_pretty(capsys: "pytest.CaptureFixture[str]") -> list[LogType]:
    capture = capsys.readouterr()
    return capture_to_logs_pretty(capture=capture)


def has_message_in_logs(logs: list[LogType], message: str) -> bool:
    return any(log for log in logs if re.search(message, log[LogKey.MESSAGE.value]))


def has_messages_in_logs(logs: list[LogType], messages: list[str]) -> bool:
    if not messages:
        return True

    log_messages = [log[LogKey.MESSAGE.value] for log in logs]
    msg_idx = 0

    for log_msg in log_messages:
        if not re.search(messages[msg_idx], log_msg):
            continue
        msg_idx += 1
        if msg_idx == len(messages):
            return True

    return False


def count_message_in_logs(logs: list[LogType], message: str) -> int:
    return sum(1 for log in logs if re.search(message, log[LogKey.MESSAGE.value]))


def find_log(logs: list[LogType], pattern: str, index: int = 0) -> LogType:
    matches = (log for log in logs if re.search(pattern, log[LogKey.MESSAGE.value]))
    for _ in range(index):
        next(matches)
    return next(matches)
