from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def examples_no_bakebook_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "no_bakebook"


@pytest.fixture(scope="session")
def examples_no_bakefile_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "no_bakefile"


@pytest.fixture(scope="session")
def examples_simple_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "simple"
