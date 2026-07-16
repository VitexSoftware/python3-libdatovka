"""Structural tests that don't require a real ISDS session."""

from __future__ import annotations

import pytest

from datovka import DatovkaClient, DatovkaError, NotLoggedInError


def test_context_lifecycle() -> None:
    with DatovkaClient(login=False) as client:
        assert client._logged_in is False
    # No exception on double-close via __del__.


def test_operations_require_login() -> None:
    with DatovkaClient(login=False) as client:
        with pytest.raises(NotLoggedInError):
            client.list_received_messages()
        with pytest.raises(NotLoggedInError):
            client.list_sent_messages()
        with pytest.raises(NotLoggedInError):
            client.get_received_message("1")
        with pytest.raises(NotLoggedInError):
            client.mark_as_read("1")


def test_bad_login_raises_datovka_error() -> None:
    with DatovkaClient(login=False) as client:
        with pytest.raises(DatovkaError):
            client.login("baduser", "badpass")
