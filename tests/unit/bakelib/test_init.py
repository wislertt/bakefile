import importlib
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


def test_version_available() -> None:
    import bakelib

    assert isinstance(bakelib.__version__, str)
    assert bakelib.__version__ != ""


def test_get_version_fallback_to_default() -> None:
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        import bakelib

        importlib.reload(bakelib)
        assert bakelib.__version__ == "0.0.0"
