"""Custom exceptions for bakefile."""


class BaseBakefileError(Exception):
    """Base exception for all bakefile errors."""


class BakebookError(BaseBakefileError):
    """Exception raised when bakebook cannot be loaded or validated (unexpected error)."""


class BakefileNotFoundError(BakebookError):
    """Exception raised when bakefile.py is not found (expected/suppressable error)."""


class PythonNotFoundError(BaseBakefileError):
    """Exception raised when Python executable cannot be found or created."""
