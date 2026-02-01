import os

import pytest

from bake.utils import ENV_NO_COLOR


@pytest.fixture(autouse=True, scope="function")
def disable_colors():
    os.environ[ENV_NO_COLOR] = "1"
