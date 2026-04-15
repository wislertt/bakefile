import logging
from collections.abc import Callable
from contextvars import ContextVar
from datetime import timezone
from itertools import product
from typing import Any, Literal
from zoneinfo import ZoneInfo

import loguru._logger
import pytest

from bake.ui.logger import capsys_to_logs, capsys_to_logs_pretty, setup_logging
from tests.unit.bake.ui.logger import module_a, module_b
from tests.unit.bake.ui.logger.utils import (
    get_number_of_logs,
    has_required_keys,
    is_log_present_as_expected,
)


def inner_test_setup_logging(
    capsys: pytest.CaptureFixture[str],
    handler_root_level: int,
    handler_module_b_level: int,
    module_a_dynamic_logger: logging.Logger | loguru._logger.Logger,
    module_a_logger_lib: Literal["logging", "loguru"],
    module_b_logger_func: Callable[[dict[str, Any] | None], None],
    module_b_logger_lib: Literal["logging", "loguru"],
    context_vars: dict[str, str | None] | None,
    extra: dict[str, Any] | None,
    is_pretty_log: bool,
):
    # setup handler/logger inputs
    level_per_module: dict[str, int] = {
        "": handler_root_level,
        module_b.NAME: handler_module_b_level,
    }

    if context_vars is not None:
        thread_local_context = {
            key: ContextVar[str | None](key, default=None) for key in context_vars
        }
        for key, value in context_vars.items():
            thread_local_context[key].set(value)
    else:
        thread_local_context = None

    setup_logging(
        level_per_module=level_per_module,
        thread_local_context=thread_local_context,
        is_pretty_log=is_pretty_log,
    )

    # log by `module_a`
    module_a.log_func_by_dynamic_logger(
        logger=module_a_dynamic_logger, logger_lib=module_a_logger_lib, extra=extra
    )

    # log by `module_b`
    module_b_logger_func(extra)

    parsed_logs = capsys_to_logs_pretty(capsys) if is_pretty_log else capsys_to_logs(capsys)

    module_a_log_count = get_number_of_logs(module_handler_level=handler_root_level)
    module_b_log_count = get_number_of_logs(module_handler_level=handler_module_b_level)

    # assert no logs
    if module_a_log_count + module_b_log_count == 0:
        assert parsed_logs == []
        return

    assert len(parsed_logs) == module_a_log_count + module_b_log_count

    for log in parsed_logs:
        assert has_required_keys(log)
        assert log["module"] in {module_a.MODULE, module_b.MODULE}

        if extra is not None:
            assert all(log.get(key) == value for key, value in extra.items())

        if context_vars is not None:
            assert all(log[key] == str(value) for key, value in context_vars.items())

        if "EXCEPTION" in log["message"]:
            assert "exc_info" in log
            assert "Traceback" in log["exc_info"]

    for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
        assert is_log_present_as_expected(
            level=level,
            handler_level=handler_root_level,
            module_name=module_a.MODULE,
            message=f"{module_a.MODULE_LOG_MESSAGE} ({logging.getLevelName(level)})",
            logs=parsed_logs,
        )

        assert is_log_present_as_expected(
            level=level,
            handler_level=handler_module_b_level,
            module_name=module_b.MODULE,
            message=(
                f"{module_b.MODULE_LOG_MESSAGE} by {module_b_logger_lib} "
                f"({logging.getLevelName(level)})"
            ),
            logs=parsed_logs,
        )

    assert is_log_present_as_expected(
        level=logging.ERROR,
        handler_level=handler_root_level,
        module_name=module_a.MODULE,
        message=f"{module_a.MODULE_LOG_MESSAGE} (EXCEPTION)",
        logs=parsed_logs,
    )

    assert is_log_present_as_expected(
        level=logging.ERROR,
        handler_level=handler_module_b_level,
        module_name=module_b.MODULE,
        message=f"{module_b.MODULE_LOG_MESSAGE} by {module_b_logger_lib} (EXCEPTION)",
        logs=parsed_logs,
    )


@pytest.mark.parametrize(
    "handler_root_level, handler_module_b_level",
    list(
        product(
            # The minimum valid logger level for a standard logging handler is 1,
            # whereas for a Loguru handler, it is 0.
            [
                100,
                logging.CRITICAL,
                logging.ERROR,
                logging.WARNING,
                logging.INFO,
                logging.DEBUG,
                1,
                0,
            ],
            [
                100,
                logging.CRITICAL,
                logging.ERROR,
                logging.WARNING,
                logging.INFO,
                logging.DEBUG,
                1,
                0,
            ],
        )
    ),
)
@pytest.mark.parametrize(
    "module_a_dynamic_logger, module_a_logger_lib, module_b_logger_func, module_b_logger_lib",
    [
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_logging, "logging"),
        (loguru.logger, "loguru", module_b.log_by_logging, "logging"),
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_loguru, "loguru"),
        (loguru.logger, "loguru", module_b.log_by_loguru, "loguru"),
    ],
)
@pytest.mark.parametrize(
    "context_vars",
    [{"tracking_id": "dummy"}],
)
@pytest.mark.parametrize(
    "extra",
    [{"some_extra": "value1", "another_key": "another_value"}],
)
def test_setup_logging(
    capsys: pytest.CaptureFixture[str],
    handler_root_level: int,
    handler_module_b_level: int,
    module_a_dynamic_logger: logging.Logger | loguru._logger.Logger,
    module_a_logger_lib: Literal["logging", "loguru"],
    module_b_logger_func: Callable[[dict[str, Any] | None], None],
    module_b_logger_lib: Literal["logging", "loguru"],
    context_vars: dict[str, str | None] | None,
    extra: dict[str, Any] | None,
):
    """Test logging with thread-local context."""
    inner_test_setup_logging(
        capsys=capsys,
        handler_root_level=handler_root_level,
        handler_module_b_level=handler_module_b_level,
        module_a_dynamic_logger=module_a_dynamic_logger,
        module_a_logger_lib=module_a_logger_lib,
        module_b_logger_func=module_b_logger_func,
        module_b_logger_lib=module_b_logger_lib,
        context_vars=context_vars,
        extra=extra,
        is_pretty_log=False,
    )


@pytest.mark.parametrize(
    "handler_root_level, handler_module_b_level",
    [(logging.INFO, logging.INFO), (logging.DEBUG, logging.INFO), (logging.INFO, logging.WARNING)],
)
@pytest.mark.parametrize(
    "module_a_dynamic_logger, module_a_logger_lib, module_b_logger_func, module_b_logger_lib",
    [
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_logging, "logging"),
        (loguru.logger, "loguru", module_b.log_by_logging, "logging"),
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_loguru, "loguru"),
        (loguru.logger, "loguru", module_b.log_by_loguru, "loguru"),
    ],
)
@pytest.mark.parametrize(
    "context_vars",
    [{"tracking_id": "dummy"}],
)
@pytest.mark.parametrize(
    "extra",
    [
        {"some_extra": "value1", "another_key": "another_value"},
        {"some_extra": "value2", "nested_key": {"sub_key": "sub_value"}},
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"empty_key": None, "another_key": "value"},
        {"nested_dict": {"sub_key1": "sub_value1", "sub_key2": "sub_value2"}},
        {"key_with_list": ["item1", "item2", "item3"], "simple_key": "simple_value"},
        {},
        None,
    ],
)
def test_setup_logging_extra(
    capsys: pytest.CaptureFixture[str],
    handler_root_level: int,
    handler_module_b_level: int,
    module_a_dynamic_logger: logging.Logger | loguru._logger.Logger,
    module_a_logger_lib: Literal["logging", "loguru"],
    module_b_logger_func: Callable[[dict[str, Any] | None], None],
    module_b_logger_lib: Literal["logging", "loguru"],
    context_vars: dict[str, str | None] | None,
    extra: dict[str, Any] | None,
):
    inner_test_setup_logging(
        capsys=capsys,
        handler_root_level=handler_root_level,
        handler_module_b_level=handler_module_b_level,
        module_a_dynamic_logger=module_a_dynamic_logger,
        module_a_logger_lib=module_a_logger_lib,
        module_b_logger_func=module_b_logger_func,
        module_b_logger_lib=module_b_logger_lib,
        context_vars=context_vars,
        extra=extra,
        is_pretty_log=False,
    )


@pytest.mark.parametrize(
    "handler_root_level, handler_module_b_level",
    [(logging.INFO, logging.INFO), (logging.DEBUG, logging.INFO), (logging.INFO, logging.WARNING)],
)
@pytest.mark.parametrize(
    "module_a_dynamic_logger, module_a_logger_lib, module_b_logger_func, module_b_logger_lib",
    [
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_logging, "logging"),
        (loguru.logger, "loguru", module_b.log_by_logging, "logging"),
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_loguru, "loguru"),
        (loguru.logger, "loguru", module_b.log_by_loguru, "loguru"),
    ],
)
@pytest.mark.parametrize(
    "context_vars",
    [
        {"tracking_id": "dummy"},
        {"tracking_id": "12345", "user_id": "user_1"},
        {"tracking_id": None, "user_id": "user_2"},
        {"session_id": "session_123", "tracking_id": "dummy", "user_id": "user_3"},
        {},
        None,
    ],
)
@pytest.mark.parametrize(
    "extra",
    [{"some_extra": "value1", "another_key": "another_value"}],
)
def test_setup_logging_thread_local_context(
    capsys: pytest.CaptureFixture[str],
    handler_root_level: int,
    handler_module_b_level: int,
    module_a_dynamic_logger: logging.Logger | loguru._logger.Logger,
    module_a_logger_lib: Literal["logging", "loguru"],
    module_b_logger_func: Callable[[dict[str, Any] | None], None],
    module_b_logger_lib: Literal["logging", "loguru"],
    context_vars: dict[str, str | None] | None,
    extra: dict[str, Any] | None,
):
    inner_test_setup_logging(
        capsys=capsys,
        handler_root_level=handler_root_level,
        handler_module_b_level=handler_module_b_level,
        module_a_dynamic_logger=module_a_dynamic_logger,
        module_a_logger_lib=module_a_logger_lib,
        module_b_logger_func=module_b_logger_func,
        module_b_logger_lib=module_b_logger_lib,
        context_vars=context_vars,
        extra=extra,
        is_pretty_log=False,
    )


@pytest.mark.parametrize(
    "handler_root_level, handler_module_b_level",
    [(logging.INFO, logging.INFO), (logging.DEBUG, logging.INFO), (logging.INFO, logging.WARNING)],
)
@pytest.mark.parametrize(
    "module_a_dynamic_logger, module_a_logger_lib, module_b_logger_func, module_b_logger_lib",
    [
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_logging, "logging"),
        (loguru.logger, "loguru", module_b.log_by_logging, "logging"),
        (logging.getLogger(module_a.NAME), "logging", module_b.log_by_loguru, "loguru"),
        (loguru.logger, "loguru", module_b.log_by_loguru, "loguru"),
    ],
)
@pytest.mark.parametrize(
    "context_vars",
    [{"tracking_id": "dummy"}],
)
@pytest.mark.parametrize(
    "extra",
    [{"some_extra": "value1", "another_key": "another_value"}],
)
def test_setup_logging_pretty_log(
    capsys: pytest.CaptureFixture[str],
    handler_root_level: int,
    handler_module_b_level: int,
    module_a_dynamic_logger: logging.Logger | loguru._logger.Logger,
    module_a_logger_lib: Literal["logging", "loguru"],
    module_b_logger_func: Callable[[dict[str, Any] | None], None],
    module_b_logger_lib: Literal["logging", "loguru"],
    context_vars: dict[str, str | None] | None,
    extra: dict[str, Any] | None,
):
    inner_test_setup_logging(
        capsys=capsys,
        handler_root_level=handler_root_level,
        handler_module_b_level=handler_module_b_level,
        module_a_dynamic_logger=module_a_dynamic_logger,
        module_a_logger_lib=module_a_logger_lib,
        module_b_logger_func=module_b_logger_func,
        module_b_logger_lib=module_b_logger_lib,
        context_vars=context_vars,
        extra=extra,
        is_pretty_log=True,
    )


class TestSetupLoggingDefaults:
    """Tests for setup_logging default values."""

    def test_setup_logging_with_default_level_per_module(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging uses WARNING level when level_per_module is None."""
        setup_logging(level_per_module=None)

        # Log at WARNING level (should be captured)
        logging.getLogger("test").warning("test warning message")

        # Log at INFO level (should NOT be captured since default is WARNING)
        logging.getLogger("test").info("test info message")

        captured = capsys.readouterr()
        output = captured.err

        assert "test warning message" in output
        assert "test info message" not in output


class TestSetupLoggingTimezone:
    """Tests for setup_logging timezone parameter."""

    def test_setup_logging_with_utc_timezone_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that setup_logging converts timestamps to UTC with JSON sink."""
        setup_logging(
            level_per_module={"": logging.INFO}, timezone=ZoneInfo("UTC"), is_pretty_log=False
        )

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # Should have +00:00 timezone offset
        assert "+00:00" in output

    def test_setup_logging_with_utc_timezone_pretty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging converts timestamps to UTC with pretty log."""
        setup_logging(
            level_per_module={"": logging.INFO}, timezone=timezone.utc, is_pretty_log=True
        )

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # Should have +00:00 timezone offset
        assert "+00:00" in output

    def test_setup_logging_with_tokyo_timezone_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging converts timestamps to Tokyo timezone with JSON sink."""
        setup_logging(
            level_per_module={"": logging.INFO},
            timezone=ZoneInfo("Asia/Tokyo"),
            is_pretty_log=False,
        )

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # Tokyo is UTC+9
        assert "+09:00" in output

    def test_setup_logging_with_none_timezone_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging uses local time when timezone=None with JSON sink."""
        from datetime import datetime

        # Get local timezone offset
        local_offset = datetime.now().astimezone().utcoffset()
        if local_offset is None:
            local_offset_str = "+00:00"
        else:
            offset_seconds = int(local_offset.total_seconds())
            sign = "+" if offset_seconds >= 0 else "-"
            hours = abs(offset_seconds) // 3600
            minutes = (abs(offset_seconds) % 3600) // 60
            local_offset_str = f"{sign}{hours:02d}:{minutes:02d}"

        setup_logging(level_per_module={"": logging.INFO}, timezone=None, is_pretty_log=False)

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # Should have local timezone offset
        assert local_offset_str in output

    def test_setup_logging_with_none_timezone_pretty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging uses local time when timezone=None with pretty log."""
        from datetime import datetime

        # Get local timezone offset
        local_offset = datetime.now().astimezone().utcoffset()
        if local_offset is None:
            local_offset_str = "+00:00"
        else:
            offset_seconds = int(local_offset.total_seconds())
            sign = "+" if offset_seconds >= 0 else "-"
            hours = abs(offset_seconds) // 3600
            minutes = (abs(offset_seconds) % 3600) // 60
            local_offset_str = f"{sign}{hours:02d}:{minutes:02d}"

        setup_logging(level_per_module={"": logging.INFO}, timezone=None, is_pretty_log=True)

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # Should have local timezone offset
        assert local_offset_str in output

    def test_setup_logging_with_new_york_timezone_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that setup_logging converts timestamps to New York timezone with JSON sink."""
        setup_logging(
            level_per_module={"": logging.INFO},
            timezone=ZoneInfo("America/New_York"),
            is_pretty_log=False,
        )

        logging.getLogger("test").info("test message")

        captured = capsys.readouterr()
        output = captured.err

        # New York is UTC-5 or UTC-4 depending on DST
        # We just check that there's a negative offset
        assert "-05:00" in output or "-04:00" in output


class TestSetupLoggingGlobalMinLogLevel:
    """Tests for setup_logging global_min_log_level parameter."""

    @pytest.mark.parametrize(
        "global_min_log_level, level_per_module, blocked_messages, allowed_messages",
        [
            # Explicit global_min_log_level=ERROR acts as strict filter
            (
                logging.ERROR,
                {"": logging.DEBUG},
                ["debug message", "info message", "warning message"],
                ["error message"],
            ),
            # global_min_log_level=None uses min from level_per_module (WARNING)
            (
                None,
                {"": logging.WARNING},
                ["debug message", "info message"],
                ["warning message"],
            ),
        ],
    )
    def test_setup_logging_global_min_log_level(
        self,
        capsys: pytest.CaptureFixture[str],
        global_min_log_level: int | None,
        level_per_module: dict[str, int],
        blocked_messages: list[str],
        allowed_messages: list[str],
    ) -> None:
        setup_logging(
            level_per_module=level_per_module,
            global_min_log_level=global_min_log_level,
        )

        logging.getLogger("test").debug("debug message")
        logging.getLogger("test").info("info message")
        logging.getLogger("test").warning("warning message")
        logging.getLogger("test").error("error message")

        captured = capsys.readouterr()
        output = captured.err

        for msg in blocked_messages:
            assert msg not in output
        for msg in allowed_messages:
            assert msg in output
