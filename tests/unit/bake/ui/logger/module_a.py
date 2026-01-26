import logging
from typing import Any, Literal

import loguru._logger

NAME = __name__
MODULE = __name__.rsplit(".", maxsplit=1)[-1]
MODULE_LOG_MESSAGE = "This is a log from module a"


def log_func_by_dynamic_logger(
    logger: logging.Logger | loguru._logger.Logger,
    logger_lib: Literal["logging", "loguru"],
    extra: dict[str, Any] | None = None,
):
    if logger_lib == "logging":
        if extra is not None:
            logger.debug(f"{MODULE_LOG_MESSAGE} (DEBUG)", extra=extra)
            logger.info(f"{MODULE_LOG_MESSAGE} (INFO)", extra=extra)
            logger.warning(f"{MODULE_LOG_MESSAGE} (WARNING)", extra=extra)
            logger.error(f"{MODULE_LOG_MESSAGE} (ERROR)", extra=extra)
            try:
                raise ValueError("Test exception")
            except Exception:
                logger.exception(f"{MODULE_LOG_MESSAGE} (EXCEPTION)", extra=extra)
        else:
            logger.debug(f"{MODULE_LOG_MESSAGE} (DEBUG)")
            logger.info(f"{MODULE_LOG_MESSAGE} (INFO)")
            logger.warning(f"{MODULE_LOG_MESSAGE} (WARNING)")
            logger.error(f"{MODULE_LOG_MESSAGE} (ERROR)")
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception(f"{MODULE_LOG_MESSAGE} (EXCEPTION)")

    elif logger_lib == "loguru":
        if extra is not None:
            logger.debug(f"{MODULE_LOG_MESSAGE} (DEBUG)", **extra)
            logger.info(f"{MODULE_LOG_MESSAGE} (INFO)", **extra)
            logger.warning(f"{MODULE_LOG_MESSAGE} (WARNING)", **extra)
            logger.error(f"{MODULE_LOG_MESSAGE} (ERROR)", **extra)
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception(f"{MODULE_LOG_MESSAGE} (EXCEPTION)", **extra)
        else:
            logger.debug(f"{MODULE_LOG_MESSAGE} (DEBUG)")
            logger.info(f"{MODULE_LOG_MESSAGE} (INFO)")
            logger.warning(f"{MODULE_LOG_MESSAGE} (WARNING)")
            logger.error(f"{MODULE_LOG_MESSAGE} (ERROR)")
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception(f"{MODULE_LOG_MESSAGE} (EXCEPTION)")
    else:
        raise ValueError("invalid `logger_lib`")
