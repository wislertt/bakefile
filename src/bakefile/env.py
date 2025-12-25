import os

ENV_NO_COLOR = "NO_COLOR"


def should_use_colors() -> bool:
    value = os.environ.get(ENV_NO_COLOR)
    return not (value == "" or value is None)
