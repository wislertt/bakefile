import logging
from collections.abc import Callable
from contextvars import ContextVar
from itertools import product
from typing import Any, Literal

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
    level_per_module = {"": handler_root_level, module_b.NAME: handler_module_b_level}

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
