import inspect
import logging
import sys
from contextvars import ContextVar
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, TextIO

import orjson
from loguru import logger
from loguru._better_exceptions import ExceptionFormatter
from loguru._simple_sinks import StreamSink

if TYPE_CHECKING:
    from loguru import FilterDict, Message, Record

    class ExtendedRecord(Record):
        default_extra: dict[str, Any]
        extra_json: str
        default_extra_json: str


UNPARSABLE_LINE = "unparsable_line"
LogType = dict[str, Any]


class LogKey(str, Enum):
    TIMESTAMP = "timestamp"
    LEVEL = "level"
    MESSAGE = "message"
    NAME = "name"
    PROCESS_NAME = "process_name"
    FILE_NAME = "file_name"
    FUNCTION_NAME = "function_name"
    LINE_NO = "line_no"
    MODULE = "module"
    THREAD_NAME = "thread_name"
    EXCEPTION = "exc_info"

    @classmethod
    def required_keys(cls) -> frozenset[str]:
        return frozenset(key.value for key in LogKey if key is not LogKey.EXCEPTION)


def get_global_min_log_level(level_per_module: "FilterDict") -> int:
    if "" not in level_per_module:
        raise ValueError("Missing empty string key for default logging level")

    if not all(isinstance(v, int) for v in level_per_module.values()):
        raise ValueError("All values in the dictionary must be of type 'int'")

    global_min_log_level = min(v for v in level_per_module.values() if isinstance(v, int))

    return global_min_log_level


def reset_all_logging_states():
    logging.root.handlers.clear()
    logging.root.setLevel(logging.NOTSET)
    for _logger in logging.Logger.manager.loggerDict.values():
        if isinstance(_logger, logging.Logger):
            _logger.handlers.clear()
            _logger.setLevel(logging.NOTSET)


class InterceptHandler(logging.Handler):
    default_log_record_attr: ClassVar[set[str]] = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        extra = {k: v for k, v in record.__dict__.items() if k not in self.default_log_record_attr}
        logger.opt(depth=depth, exception=record.exc_info).bind(**extra).log(
            level, record.getMessage()
        )


def to_json_serializable(data: Any) -> Any:
    return orjson.dumps(data, default=str).decode()


def flatten_extra(record_extra: dict[str, Any]) -> dict[str, Any]:
    # Maintain consistent extra= API between standard logging and Loguru
    # Flatten Loguru's nested structure to match logging module behavior
    if "extra" in record_extra:
        nested_extra = record_extra.pop("extra")
        record_extra.update(
            {f"extra_{k}" if k in record_extra else k: v for k, v in nested_extra.items()}
        )

    return record_extra


class PrettyLogFormatter:
    def __init__(self, thread_local_context: dict[str, ContextVar[Any]]):
        self.thread_local_context = thread_local_context

    def __call__(self, record: "ExtendedRecord"):
        thread_local_extra = {}
        for context_var_name, context_var in self.thread_local_context.items():
            thread_local_extra[context_var_name] = str(context_var.get())

        record["extra"] = flatten_extra(record["extra"])
        record["extra"] = {**thread_local_extra, **record["extra"]}
        # Ensure all values are JSON-serializable (e.g., PosixPath -> str)
        record["extra_json"] = orjson.dumps(record["extra"], default=str).decode()

        record["default_extra"] = {
            "process_name": record["process"].name,
            "file_name": record["file"].name,
            "thread_name": record["thread"].name,
        }
        record["default_extra_json"] = orjson.dumps(record["default_extra"], default=str).decode()

        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS Z}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level> - "
            "<cyan>{extra_json}</cyan> - "
            "<light-black>{default_extra_json}</light-black>\n"
        ) + ("\n{exception}\n\n" if record["exception"] else "")


class JsonSink(StreamSink):
    def __init__(
        self,
        thread_local_context: dict[str, ContextVar[Any]] | None = None,
        stream: TextIO | Any = None,
    ):
        # sys.stderr is mutable object
        if stream is None:
            stream = sys.stderr
        super().__init__(stream)

        if thread_local_context is None:
            thread_local_context = {}

        self.thread_local_context = thread_local_context

    def write(self, message: "Message"):
        record = message.record
        log_entry = self.json_formatter(record=record)
        log_message = orjson.dumps(
            log_entry, default=str, option=orjson.OPT_APPEND_NEWLINE
        ).decode()
        return super().write(log_message)

    def json_formatter(self, record: "Record") -> LogType:
        log_entry: LogType = {
            LogKey.TIMESTAMP.value: record["time"],
            LogKey.LEVEL.value: record["level"].name,
            LogKey.MESSAGE.value: record["message"],
            LogKey.NAME.value: record["name"],
            LogKey.PROCESS_NAME.value: record["process"].name,
            LogKey.FILE_NAME.value: record["file"].name,
            LogKey.FUNCTION_NAME.value: record["function"],
            LogKey.LINE_NO.value: record["line"],
            LogKey.MODULE.value: record["module"],
            LogKey.THREAD_NAME.value: record["thread"].name,
        }

        for context_var_name, context_vars in self.thread_local_context.items():
            log_entry[context_var_name] = str(context_vars.get())

        if record["exception"] is not None:
            log_entry[LogKey.EXCEPTION.value] = "".join(
                ExceptionFormatter().format_exception(
                    type_=record["exception"][0],
                    value=record["exception"][1],
                    tb=record["exception"][2],
                )
            )

        record["extra"] = flatten_extra(record["extra"])
        log_entry.update(record["extra"])
        return log_entry
