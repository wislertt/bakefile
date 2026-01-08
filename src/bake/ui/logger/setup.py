import logging
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, cast

from loguru import logger

from .utils import (
    InterceptHandler,
    JsonSink,
    PrettyLogFormatter,
    get_global_min_log_level,
    reset_all_logging_states,
)

if TYPE_CHECKING:
    from loguru import FilterDict, FormatFunction


def setup_logging(
    level_per_module: "FilterDict | None" = None,
    thread_local_context: dict[str, ContextVar[Any]] | None = None,
    is_pretty_log: bool = False,
) -> None:
    if level_per_module is None:
        level_per_module = {"": logging.WARNING}

    if thread_local_context is None:
        thread_local_context = {}

    global_min_log_level = get_global_min_log_level(level_per_module)

    reset_all_logging_states()
    logger.remove()
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    if is_pretty_log:
        sink = sys.stderr
        formatter: FormatFunction | str = cast(
            "FormatFunction",
            PrettyLogFormatter(thread_local_context=thread_local_context),
        )
    else:
        sink = JsonSink(thread_local_context=thread_local_context)
        formatter: FormatFunction | str = ""

    logger.add(
        sink=sink,
        format=formatter,
        level=global_min_log_level,
        filter=level_per_module,
        backtrace=False,
    )
