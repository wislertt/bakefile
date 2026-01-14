import loguru
import pytest

from bake.ui.logger.utils import reset_all_logging_states


@pytest.fixture(scope="function")
def reset_all_logger_state():
    yield
    loguru.logger.remove()
    reset_all_logging_states()
