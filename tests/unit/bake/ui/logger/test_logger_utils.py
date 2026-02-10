import logging
from contextvars import ContextVar
from datetime import datetime
from unittest.mock import patch

import loguru
import pytest

from bake.ui.logger.utils import (
    InterceptHandler,
    JsonSink,
    PrettyLogFormatter,
    flatten_extra,
    get_global_min_log_level,
    reset_all_logging_states,
    to_json_serializable,
)

# ==============================================================================
# Tests for individual components
# ==============================================================================


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
        level_per_module = {"": logging.WARNING, "test_module": logging.DEBUG}
        result = get_global_min_log_level(level_per_module)
        assert result == logging.DEBUG

    def test_raises_on_missing_default_key(self) -> None:
        """Test that function raises ValueError when '' key is missing."""
        level_per_module = {"test_module": logging.WARNING}
        with pytest.raises(ValueError, match="Missing empty string key"):
            get_global_min_log_level(level_per_module)

    def test_raises_on_non_int_values(self) -> None:
        """Test that function raises ValueError on non-int values."""
        level_per_module = {"": logging.WARNING, "test": "INFO"}
        with pytest.raises(ValueError, match=r"All values.*must be of type 'int'"):
            get_global_min_log_level(level_per_module)

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
        assert get_global_min_log_level(levels) == expected_min  # type: ignore[arg-type]


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

        result = formatter(record)  # type: ignore[arg-type]
        assert isinstance(result, str)
        assert len(result) > 0


class TestToJsonSerializable:
    """Tests for to_json_serializable function."""

    def test_returns_json_string(self) -> None:
        """Test that to_json_serializable returns JSON string."""
        result = to_json_serializable({"key": "value"})
        assert isinstance(result, str)
        assert result == '{"key":"value"}'

    def test_handles_non_serializable_objects(self) -> None:
        """Test that to_json_serializable handles non-serializable objects."""
        from pathlib import Path

        result = to_json_serializable({"path": Path("/test/path")})
        assert isinstance(result, str)
        # Check that the path key exists and contains path components (cross-platform)
        assert '"path"' in result
        assert "test" in result


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
