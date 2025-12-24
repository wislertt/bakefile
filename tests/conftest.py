from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def examples_simple_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "simple"
