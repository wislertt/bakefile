import sys
from datetime import datetime
from pathlib import Path

import pydantic


class GreetingMessage(pydantic.BaseModel):
    message: str
    timestamp: datetime
    python_version: str
    directory: str


def hello(test_test: None = None) -> str:
    _ = test_test
    current_time = datetime.now()
    current_dir = str(Path.cwd())
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    greeting = GreetingMessage(
        message="Hello from bakefile!",
        timestamp=current_time,
        python_version=python_version,
        directory=current_dir,
    )

    return (
        f"{greeting.message}\n"
        f"Current time: {greeting.timestamp}\n"
        f"Current directory: {greeting.directory}\n"
        f"Python version: {greeting.python_version}"
    )
