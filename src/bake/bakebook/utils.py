import logging

from loguru import logger

from bake.utils.constants import DEFAULT_BAKE_LOG

_LOG_LEVEL_NAME_TO_NUMBER_MAP: dict[str, int] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "success": logger.level("SUCCESS").no,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "trace": logger.level("TRACE").no,
    "notset": logging.NOTSET,
}

_LOG_LEVEL_NUMBER_TO_NAME_MAP: dict[int, str] = {
    number: name for name, number in _LOG_LEVEL_NAME_TO_NUMBER_MAP.items()
}


def _parse_level(level_name: str, part: str) -> int:
    level_lower = level_name.lower()
    if level_lower not in _LOG_LEVEL_NAME_TO_NUMBER_MAP:
        sorted_levels = sorted(
            _LOG_LEVEL_NAME_TO_NUMBER_MAP.keys(),
            key=lambda k: _LOG_LEVEL_NAME_TO_NUMBER_MAP[k],
        )
        raise ValueError(
            f"Invalid BAKE_LOG level '{level_name}' in '{part}'. "
            f"Valid levels: {', '.join(sorted_levels)}"
        )
    return _LOG_LEVEL_NAME_TO_NUMBER_MAP[level_lower]


def parse_bake_log(bake_log: str) -> dict[str, int]:
    if not bake_log:
        raise ValueError(f"BAKE_LOG must be a non-empty string (e.g., '{DEFAULT_BAKE_LOG}')")

    level_per_module: dict[str, int] = {}

    for part in bake_log.split(","):
        part = part.strip()
        if not part:
            continue

        if "=" in part:
            module, level_name = part.split("=", 1)
            module = module.strip()
            if not module:
                raise ValueError(f"Invalid BAKE_LOG format: empty module name in '{part}'")
            level_per_module[module] = _parse_level(level_name.strip(), part)
        else:
            level_per_module[""] = _parse_level(part, part)

    if "" not in level_per_module:
        raise ValueError(
            f"BAKE_LOG must contain a default logging level (e.g., '{DEFAULT_BAKE_LOG}')"
        )

    return level_per_module


def serialize_bake_log(level_per_module: dict[str, int]) -> str:
    if not level_per_module:
        raise ValueError("BAKE_LOG config must be a non-empty dict")
    if "" not in level_per_module:
        raise ValueError("BAKE_LOG config must contain a default logging level (key '')")

    default_level = level_per_module[""]
    default_name = _LOG_LEVEL_NUMBER_TO_NAME_MAP[default_level]

    parts: list[str] = [default_name]
    for module, level in level_per_module.items():
        if module == "":
            continue
        level_name = _LOG_LEVEL_NUMBER_TO_NAME_MAP[level]
        parts.append(f"{module}={level_name}")
    return ",".join(parts)
