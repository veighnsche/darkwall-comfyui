"""History module exceptions."""

from ..exceptions import DarkWallError


class HistoryError(DarkWallError):
    """Base exception for history management errors."""
    pass


class HistoryConfigError(HistoryError):
    """History configuration error."""
    pass


class HistoryStorageError(HistoryError):
    """History storage/filesystem error."""
    pass
