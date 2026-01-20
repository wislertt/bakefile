from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def examples_simple_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "simple"


@pytest.fixture(scope="session")
def examples_python_package_dir() -> Path:
    return Path(__file__).parent.parent.parent / "examples" / "python-package"
