from enum import Enum
from typing import TYPE_CHECKING

from .utils import JsonSink, LogKey, LogKeyMixin, LogType

if TYPE_CHECKING:
    from loguru import Record


class GCPLogKey(LogKeyMixin, str, Enum):
    TIME = "time"
    SEVERITY = "severity"

    @classmethod
    def required_keys(cls) -> frozenset[str]:
        return cls._required_keys([LogKey])


class GCPJsonSink(JsonSink):
    def json_formatter(self, record: "Record") -> LogType:
        log_entry = super().json_formatter(record)

        # GCP requires these field names
        log_entry[GCPLogKey.TIME.value] = log_entry[LogKey.TIMESTAMP.value]
        log_entry[GCPLogKey.SEVERITY.value] = log_entry[LogKey.LEVEL.value].upper()

        return log_entry
