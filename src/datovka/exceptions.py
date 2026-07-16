"""Exceptions raised by the datovka package."""

from __future__ import annotations


class DatovkaError(Exception):
    """Raised when a libdatovka call fails.

    Attributes:
        code: The numeric ``isds_error`` value returned by libdatovka.
        message: Short description from ``isds_strerror()``.
        detail: Longer, context-specific message from ``isds_long_message()``,
            if libdatovka provided one.
    """

    def __init__(self, code: int, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        text = message if code else "unknown libdatovka error"
        if detail and detail != message:
            text = f"{text}: {detail}"
        super().__init__(text)


class NotLoggedInError(DatovkaError):
    """Raised when an operation is attempted without an active session."""
