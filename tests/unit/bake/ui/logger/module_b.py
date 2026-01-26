import logging
from typing import Any

import loguru

# Setting up logger for the logging module
logger = logging.getLogger(__name__)

NAME = __name__
MODULE = __name__.rsplit(".", maxsplit=1)[-1]
MODULE_LOG_MESSAGE = "This is a log from module b"


def log_by_logging(extra: dict[str, Any] | None = None):
    logger_lib = "logging"
    if extra is not None:
        logger.debug("%s by %s (DEBUG)", MODULE_LOG_MESSAGE, logger_lib, extra=extra)
        logger.info("%s by %s (INFO)", MODULE_LOG_MESSAGE, logger_lib, extra=extra)
        logger.warning("%s by %s (WARNING)", MODULE_LOG_MESSAGE, logger_lib, extra=extra)
        logger.error("%s by %s (ERROR)", MODULE_LOG_MESSAGE, logger_lib, extra=extra)
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("%s by %s (EXCEPTION)", MODULE_LOG_MESSAGE, logger_lib, extra=extra)
    else:
        logger.debug("%s by %s (DEBUG)", MODULE_LOG_MESSAGE, logger_lib)
        logger.info("%s by %s (INFO)", MODULE_LOG_MESSAGE, logger_lib)
        logger.warning("%s by %s (WARNING)", MODULE_LOG_MESSAGE, logger_lib)
        logger.error("%s by %s (ERROR)", MODULE_LOG_MESSAGE, logger_lib)
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("%s by %s (EXCEPTION)", MODULE_LOG_MESSAGE, logger_lib)


def log_by_loguru(extra: dict[str, Any] | None = None):
    logger_lib = "loguru"
    if extra is not None:
        loguru.logger.debug(f"{MODULE_LOG_MESSAGE} by {logger_lib} (DEBUG)", **extra)
        loguru.logger.info(f"{MODULE_LOG_MESSAGE} by {logger_lib} (INFO)", **extra)
        loguru.logger.warning(f"{MODULE_LOG_MESSAGE} by {logger_lib} (WARNING)", **extra)
        loguru.logger.error(f"{MODULE_LOG_MESSAGE} by {logger_lib} (ERROR)", **extra)
        try:
            raise ValueError("Test exception")
        except ValueError:
            loguru.logger.exception(f"{MODULE_LOG_MESSAGE} by {logger_lib} (EXCEPTION)", **extra)
    else:
        loguru.logger.debug(f"{MODULE_LOG_MESSAGE} by {logger_lib} (DEBUG)")
        loguru.logger.info(f"{MODULE_LOG_MESSAGE} by {logger_lib} (INFO)")
        loguru.logger.warning(f"{MODULE_LOG_MESSAGE} by {logger_lib} (WARNING)")
        loguru.logger.error(f"{MODULE_LOG_MESSAGE} by {logger_lib} (ERROR)")
        try:
            raise ValueError("Test exception")
        except ValueError:
            loguru.logger.exception(f"{MODULE_LOG_MESSAGE} by {logger_lib} (EXCEPTION)")
