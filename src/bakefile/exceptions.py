"""Custom exceptions for bakefile."""


class BaseBakefileError(Exception):
    """Base exception for all bakefile errors."""


class BakebookError(BaseBakefileError):
    """Exception raised when bakebook cannot be loaded or validated."""
