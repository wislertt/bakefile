import logging
from typing import Any

from bake.ui.logger.utils import LogKey


def is_log_present_as_expected(
    level: int,
    handler_level: int,
    module_name: str,
    message: str,
    logs: list[dict],
) -> bool:
    module_logs = [log[LogKey.MESSAGE] for log in logs if log[LogKey.MODULE] == module_name]
    is_log_present = message in module_logs
    should_be_present = level >= handler_level
    correctly_present = is_log_present == should_be_present

    return correctly_present


def get_number_of_logs(
    module_handler_level: int,
) -> int:
    logger_levels = [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.ERROR,  # exception
    ]
    handled_log_levels = [level for level in logger_levels if level >= module_handler_level]
    return len(handled_log_levels)


def has_required_keys(log: dict[str, Any]) -> bool:
    return LogKey.required_keys().issubset(log.keys())
