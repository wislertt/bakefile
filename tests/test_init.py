from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


def test_get_version_fallback_to_default() -> None:
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        # Re-import to trigger the fallback
        import importlib

        import bakefile

        importlib.reload(bakefile)
        assert bakefile.__version__ == "0.0.0"
