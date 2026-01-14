"""Test helper utilities for decorators and common test patterns."""

import os
import sys
from functools import wraps


def flaky_on_macos_ci(max_retries: int = 3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            is_macos = sys.platform == "darwin"
            is_ci = os.getenv("CI") == "true"

            if not (is_macos and is_ci):
                return func(*args, **kwargs)

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except AssertionError:
                    if attempt == max_retries - 1:
                        raise
            return None

        return wrapper

    return decorator
