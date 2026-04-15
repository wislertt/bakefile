import logging
import sys
from contextvars import ContextVar
from datetime import tzinfo
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
    level_per_module: dict[str, int] | None = None,
    thread_local_context: dict[str, ContextVar[Any]] | None = None,
    is_pretty_log: bool = False,
    json_sink_class: type[JsonSink] | None = None,
    pretty_log_formatter_class: type[PrettyLogFormatter] | None = None,
    timezone: tzinfo | None = None,
    global_min_log_level: int | None = None,
) -> None:
    if level_per_module is None:
        level_per_module = {"": logging.WARNING}

    if thread_local_context is None:
        thread_local_context = {}

    if global_min_log_level is None:
        global_min_log_level = get_global_min_log_level(level_per_module)

    reset_all_logging_states()
    logger.remove()
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    if is_pretty_log:
        sink = sys.stderr
        formatter: FormatFunction | str = cast(
            "FormatFunction",
            (pretty_log_formatter_class or PrettyLogFormatter)(
                thread_local_context=thread_local_context, timezone=timezone
            ),
        )
    else:
        sink = (json_sink_class or JsonSink)(
            thread_local_context=thread_local_context, timezone=timezone
        )
        formatter: FormatFunction | str = ""

    logger.add(
        sink=sink,
        format=formatter,
        level=global_min_log_level,
        filter=cast("FilterDict", level_per_module),
        backtrace=False,
    )
