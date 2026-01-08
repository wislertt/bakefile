import os

import pytest

from bake.utils.env import ENV_NO_COLOR


@pytest.fixture(autouse=True)
def disable_colors():
    os.environ[ENV_NO_COLOR] = "1"
