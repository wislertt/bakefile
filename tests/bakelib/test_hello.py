import pytest

import bakelib

pytest.importorskip("requests")


def test_hello_world() -> None:
    """Test that hello_world makes HTTP request and returns expected string."""
    result = bakelib.hello_world()
    assert "Hello from bakelib!" in result
    assert "Status:" in result
    assert "200" in result
