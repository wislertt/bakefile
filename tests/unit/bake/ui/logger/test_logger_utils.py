import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import loguru
import pytest

from bake.ui.logger.utils import (
    InterceptHandler,
    JsonSink,
    LogKey,
    LogKeyMixin,
    PrettyLogFormatter,
    flatten_extra,
    get_global_min_log_level,
    reset_all_logging_states,
)

# ==============================================================================
# Tests for individual components
# ==============================================================================


class TestLogKeyMixin:
    """Tests for LogKeyMixin class."""

    def test_required_keys_raises_not_implemented(self) -> None:
        """Test that LogKeyMixin.required_keys() raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            LogKeyMixin.required_keys()

    def test_required_keys_returns_frozenset(self) -> None:
        """Test that LogKey.required_keys() returns a frozenset."""
        result = LogKey.required_keys()
        assert isinstance(result, frozenset)

    def test_required_keys_excludes_exception(self) -> None:
        """Test that LogKey.required_keys() excludes EXCEPTION key."""
        result = LogKey.required_keys()
        assert LogKey.EXCEPTION.value not in result
        assert LogKey.TIMESTAMP.value in result
        assert LogKey.LEVEL.value in result
        assert LogKey.MESSAGE.value in result


class TestInterceptHandler:
    """Tests for InterceptHandler class."""

    def test_intercept_handler_is_logging_handler(self) -> None:
        """Test that InterceptHandler is a logging.Handler instance."""
        handler = InterceptHandler()
        assert isinstance(handler, logging.Handler)

    def test_intercept_handler_has_emit_method(self) -> None:
        """Test that InterceptHandler has an emit method."""
        handler = InterceptHandler()
        assert hasattr(handler, "emit")

    def test_intercept_handler_has_default_log_record_attr(self) -> None:
        """Test that InterceptHandler has default_log_record_attr set."""
        assert hasattr(InterceptHandler, "default_log_record_attr")
        assert isinstance(InterceptHandler.default_log_record_attr, set)
        assert "name" in InterceptHandler.default_log_record_attr
        assert "levelname" in InterceptHandler.default_log_record_attr


class TestGetGlobalMinLogLevel:
    """Tests for get_global_min_log_level function."""

    def test_returns_min_level(self) -> None:
        """Test that function returns minimum log level."""
        level_per_module: dict[str, int] = {"": logging.WARNING, "test_module": logging.DEBUG}
        result: int = get_global_min_log_level(level_per_module)
        assert result == logging.DEBUG

    def test_raises_on_missing_default_key(self) -> None:
        """Test that function raises ValueError when '' key is missing."""
        level_per_module: dict[str, int] = {"test_module": logging.WARNING}
        with pytest.raises(ValueError, match="Missing empty string key"):
            get_global_min_log_level(level_per_module)

    def test_raises_on_non_int_values(self) -> None:
        """Test that function raises ValueError on non-int values."""
        level_per_module: dict[str, int | str] = {"": logging.WARNING, "test": "INFO"}
        with pytest.raises(ValueError, match=r"All values.*must be of type 'int'"):
            get_global_min_log_level(level_per_module)  # ty: ignore[invalid-argument-type]

    @pytest.mark.parametrize(
        "levels,expected_min",
        [
            ({"": logging.INFO}, logging.INFO),
            ({"": logging.ERROR, "a": logging.WARNING}, logging.WARNING),
            ({"": logging.DEBUG, "a": logging.INFO, "b": logging.ERROR}, logging.DEBUG),
            ({"": logging.CRITICAL, "a": logging.CRITICAL}, logging.CRITICAL),
        ],
    )
    def test_various_level_combinations(self, levels: dict[str, int], expected_min: int) -> None:
        """Test various combinations of log levels."""
        assert get_global_min_log_level(levels) == expected_min


class TestResetAllLoggingStates:
    """Tests for reset_all_logging_states function."""

    def test_clears_root_logger_handlers(self) -> None:
        """Test that function clears root logger handlers."""
        logging.root.addHandler(logging.StreamHandler())
        assert len(logging.root.handlers) > 0

        reset_all_logging_states()
        assert len(logging.root.handlers) == 0

    def test_resets_root_logger_level(self) -> None:
        """Test that function resets root logger level."""
        logging.root.setLevel(logging.ERROR)
        assert logging.root.level == logging.ERROR

        reset_all_logging_states()
        assert logging.root.level == logging.NOTSET

    def test_clears_child_logger_handlers(self) -> None:
        """Test that function clears child logger handlers."""
        child_logger = logging.getLogger("test_child")
        child_logger.addHandler(logging.StreamHandler())
        assert len(child_logger.handlers) > 0

        reset_all_logging_states()
        assert len(child_logger.handlers) == 0

    def test_resets_child_logger_level(self) -> None:
        """Test that function resets child logger level."""
        child_logger = logging.getLogger("test_child")
        child_logger.setLevel(logging.ERROR)
        assert child_logger.level == logging.ERROR

        reset_all_logging_states()
        assert child_logger.level == logging.NOTSET


class TestFlattenExtra:
    """Tests for flatten_extra function."""

    def test_returns_empty_dict_for_empty_input(self) -> None:
        """Test that function returns empty dict for empty input."""
        result = flatten_extra({})
        assert result == {}

    def test_returns_dict_unchanged_when_no_extra_key(self) -> None:
        """Test that function returns dict unchanged when no 'extra' key."""
        result = flatten_extra({"key1": "value1", "key2": "value2"})
        assert result == {"key1": "value1", "key2": "value2"}

    def test_flattens_nested_extra_dict(self) -> None:
        """Test that function flattens nested 'extra' dict."""
        result = flatten_extra({"extra": {"nested_key": "nested_value"}})
        assert result == {"nested_key": "nested_value"}

    def test_adds_prefix_to_duplicate_keys(self) -> None:
        """Test that function adds 'extra_' prefix to duplicate keys."""
        result = flatten_extra({"key": "value1", "extra": {"key": "value2"}})
        assert result == {"key": "value1", "extra_key": "value2"}

    def test_handles_multiple_nested_keys(self) -> None:
        """Test that function handles multiple nested keys."""
        result = flatten_extra(
            {
                "key1": "value1",
                "key2": "value2",
                "extra": {"key2": "nested_value2", "key3": "nested_value3"},
            }
        )
        assert result == {
            "key1": "value1",
            "key2": "value2",
            "extra_key2": "nested_value2",
            "key3": "nested_value3",
        }

    def test_handles_deeply_nested_extra(self) -> None:
        """Test that function handles deeply nested 'extra' (only one level)."""
        # Only flattens one level from loguru's bind()
        result = flatten_extra({"extra": {"key1": {"subkey": "value"}}})
        assert result == {"key1": {"subkey": "value"}}


class TestJsonSink:
    """Tests for JsonSink class."""

    def test_json_sink_inherits_from_stream_sink(self) -> None:
        """Test that JsonSink inherits from StreamSink."""
        from loguru._simple_sinks import StreamSink

        sink = JsonSink()
        assert isinstance(sink, StreamSink)

    def test_json_sink_has_write_method(self) -> None:
        """Test that JsonSink has a write method."""
        sink = JsonSink()
        assert hasattr(sink, "write")

    def test_json_sink_accepts_thread_local_context(self) -> None:
        """Test that JsonSink accepts thread_local_context parameter."""
        context_var = ContextVar("test", default=None)
        sink = JsonSink(thread_local_context={"test": context_var})
        assert sink.thread_local_context == {"test": context_var}

    def test_json_sink_accepts_timezone(self) -> None:
        """Test that JsonSink accepts timezone parameter."""
        sink = JsonSink(timezone=ZoneInfo("UTC"))
        assert sink.timezone == ZoneInfo("UTC")

    def test_json_sink_timezone_none_by_default(self) -> None:
        """Test that JsonSink has timezone=None by default."""
        sink = JsonSink()
        assert sink.timezone is None

    def test_json_sink_json_formatter_converts_to_utc(self) -> None:
        """Test that JsonSink.json_formatter converts timestamp to UTC."""
        import multiprocessing
        import pathlib
        import threading

        sink = JsonSink(timezone=timezone.utc)

        record = {
            "time": datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok")),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "module": "test_module",
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        result = sink.json_formatter(record)  # ty: ignore[invalid-argument-type]

        # Bangkok is UTC+7, so 17:00 becomes 10:00 UTC
        assert result["timestamp"].hour == 10
        assert result["timestamp"].tzinfo == timezone.utc

    def test_json_sink_json_formatter_no_timezone_conversion_when_none(self) -> None:
        """Test that JsonSink.json_formatter does not convert timezone when None."""
        import multiprocessing
        import pathlib
        import threading

        sink = JsonSink(timezone=None)

        local_time = datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok"))
        record = {
            "time": local_time,
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "module": "test_module",
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        result = sink.json_formatter(record)  # ty: ignore[invalid-argument-type]

        # Should keep original time
        assert result["timestamp"].hour == 17
        assert result["timestamp"].tzinfo == ZoneInfo("Asia/Bangkok")

    def test_json_sink_unset_context_var_does_not_raise(self) -> None:
        """Unset ContextVar (no default) logs as None instead of raising LookupError."""
        import multiprocessing
        import pathlib
        import threading

        unset_var = ContextVar("unset_var")  # no default, never .set()
        sink = JsonSink(thread_local_context={"unset_var": unset_var})

        record = {
            "time": datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok")),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "module": "test_module",
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        result = sink.json_formatter(record)  # ty: ignore[invalid-argument-type]

        assert result["unset_var"] == str(None)

    def test_json_sink_context_var_creation_default_preserved(self) -> None:
        """ContextVar.get() returns creation default when unset (not overridden by None)."""
        import multiprocessing
        import pathlib
        import threading

        task_var = ContextVar("task", default="unknown")
        sink = JsonSink(thread_local_context={"task": task_var})

        record = {
            "time": datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok")),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "module": "test_module",
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        result = sink.json_formatter(record)  # ty: ignore[invalid-argument-type]

        assert result["task"] == "unknown"


class TestPrettyLogFormatter:
    """Tests for PrettyLogFormatter class."""

    def test_pretty_log_formatter_has_call_method(self) -> None:
        """Test that PrettyLogFormatter has a __call__ method."""
        formatter = PrettyLogFormatter(thread_local_context={})
        assert callable(formatter)

    def test_pretty_log_formatter_accepts_thread_local_context(self) -> None:
        """Test that PrettyLogFormatter accepts thread_local_context parameter."""
        context_var = ContextVar("test", default=None)
        formatter = PrettyLogFormatter(thread_local_context={"test": context_var})
        assert formatter.thread_local_context == {"test": context_var}

    def test_pretty_log_formatter_returns_string(self) -> None:
        """Test that PrettyLogFormatter returns a string."""
        formatter = PrettyLogFormatter(thread_local_context={})

        # Create a minimal record dict (simplified for testing)
        import multiprocessing
        import pathlib
        import threading

        record = {
            "time": datetime.now(),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        result = formatter(record)  # ty: ignore[invalid-argument-type]
        assert isinstance(result, str)
        assert len(result) > 0

    def test_pretty_log_formatter_accepts_timezone(self) -> None:
        """Test that PrettyLogFormatter accepts timezone parameter."""
        formatter = PrettyLogFormatter(thread_local_context={}, timezone=ZoneInfo("UTC"))
        assert formatter.timezone == ZoneInfo("UTC")

    def test_pretty_log_formatter_timezone_none_by_default(self) -> None:
        """Test that PrettyLogFormatter has timezone=None by default."""
        formatter = PrettyLogFormatter(thread_local_context={})
        assert formatter.timezone is None

    def test_pretty_log_formatter_converts_to_utc(self) -> None:
        """Test that PrettyLogFormatter converts timestamp to UTC."""
        import multiprocessing
        import pathlib
        import threading

        formatter = PrettyLogFormatter(thread_local_context={}, timezone=timezone.utc)

        record = {
            "time": datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok")),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        formatter(record)  # ty: ignore[invalid-argument-type]

        # Bangkok is UTC+7, so 17:00 becomes 10:00 UTC
        assert record["time"].hour == 10
        assert record["time"].tzinfo == timezone.utc

    def test_pretty_log_formatter_no_timezone_conversion_when_none(self) -> None:
        """Test that PrettyLogFormatter does not convert timezone when None."""
        import multiprocessing
        import pathlib
        import threading

        formatter = PrettyLogFormatter(thread_local_context={}, timezone=None)

        local_time = datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok"))
        record = {
            "time": local_time,
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        formatter(record)  # ty: ignore[invalid-argument-type]

        # Should keep original time
        assert record["time"].hour == 17
        assert record["time"].tzinfo == ZoneInfo("Asia/Bangkok")

    def test_pretty_log_formatter_unset_context_var_does_not_raise(self) -> None:
        """Unset ContextVar (no default) logs as None instead of raising LookupError."""
        import multiprocessing
        import pathlib
        import threading

        unset_var = ContextVar("unset_var")  # no default, never .set()
        formatter = PrettyLogFormatter(thread_local_context={"unset_var": unset_var})

        record = {
            "time": datetime(2026, 4, 12, 17, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok")),
            "level": loguru.logger.level("INFO"),
            "message": "Test message",
            "name": "test",
            "process": multiprocessing.current_process(),
            "file": pathlib.Path(__file__),
            "function": "test_function",
            "line": 42,
            "thread": threading.current_thread(),
            "extra": {},
            "exception": None,
        }

        formatter(record)  # ty: ignore[invalid-argument-type]

        assert record["extra"]["unset_var"] == str(None)


class TestInterceptHandlerEmit:
    """Tests for InterceptHandler.emit method edge cases."""

    def test_emit_handles_unknown_log_level(self) -> None:
        """Test that emit handles unknown log levels (ValueError case)."""
        handler = InterceptHandler()

        # Create a LogRecord with a level name that doesn't exist in loguru
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,  # Use standard level number
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Change levelname to something that doesn't exist in loguru
        record.levelname = "UNKNOWN_LEVEL_999"

        # Mock logger.level to raise ValueError for unknown level
        with patch("bake.ui.logger.utils.logger.level") as mock_level:
            mock_level.side_effect = ValueError("Unknown level")
            handler.emit(record)

        # Verify the record was still logged (using levelno as fallback)
        # We just check it doesn't raise an exception
