import os
from pathlib import Path

import pytest

from bakefile.constants import ENV_NO_COLOR


@pytest.fixture(autouse=True)
def disable_colors():
    """Disable colored output in tests for consistent assertions."""
    os.environ[ENV_NO_COLOR] = "1"


@pytest.fixture(scope="session")
def examples_no_bakebook_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "no_bakebook"


@pytest.fixture(scope="session")
def examples_no_bakefile_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "no_bakefile"


@pytest.fixture(scope="session")
def examples_simple_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "simple"
