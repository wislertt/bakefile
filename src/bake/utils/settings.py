import logging
import sys
from contextvars import ContextVar
from datetime import tzinfo
from typing import Any, Literal

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

from bake.bakebook.utils import parse_bake_log
from bake.ui.logger.setup import setup_logging
from bake.ui.logger.utils import JsonSink, PrettyLogFormatter

ENV_NO_COLOR = "NO_COLOR"
ENV__BAKE_REINVOKED = "_BAKE_REINVOKED"

PlatformType = Literal["macos", "linux", "windows", "other"]


def _detect_platform() -> PlatformType:
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "linux":
        return "linux"
    elif sys.platform == "win32":
        return "windows"
    return "other"


_VERBOSITY_TO_LOG_LEVEL: dict[int, int] = {
    0: logging.CRITICAL + 1,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}
_LOG_LEVELS_TO_VERBOSITY: dict[int, int] = {v: k for k, v in _VERBOSITY_TO_LOG_LEVEL.items()}


class BakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    ci: bool = False
    github_actions: bool = False
    no_color: bool = False
    platform: PlatformType = Field(default_factory=_detect_platform)
    bake_reinvoked: bool = Field(default=False, alias=ENV__BAKE_REINVOKED)
    _bake_logging_setup: bool = PrivateAttr(default=False)

    def should_use_colors(self) -> bool:
        return self.no_color

    def setup_bake_logging(
        self,
        bake_log: str,
        verbosity: int,
        bake_log_pretty: bool,
        thread_local_context: dict[str, ContextVar[Any]] | None = None,
        json_sink_class: type[JsonSink] | None = None,
        pretty_log_formatter_class: type[PrettyLogFormatter] | None = None,
        timezone: tzinfo | None = None,
    ) -> None:
        if self._bake_logging_setup:
            return

        setup_logging(
            level_per_module=parse_bake_log(bake_log),
            thread_local_context=thread_local_context,
            is_pretty_log=bake_log_pretty,
            json_sink_class=json_sink_class,
            pretty_log_formatter_class=pretty_log_formatter_class,
            timezone=timezone,
            global_min_log_level=_VERBOSITY_TO_LOG_LEVEL[verbosity],
        )
        self._bake_logging_setup = True


bake_settings = BakeSettings()
