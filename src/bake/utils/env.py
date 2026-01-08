import os

ENV_NO_COLOR = "NO_COLOR"

_BAKE_REINVOKED = "_BAKE_REINVOKED"


def should_use_colors() -> bool:
    value = os.environ.get(ENV_NO_COLOR)
    return value == "" or value is None
