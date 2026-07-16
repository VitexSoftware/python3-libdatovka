"""Structural tests that don't require a real ISDS session."""

from __future__ import annotations

import pytest

from datovka import DatovkaClient, DatovkaError, NotLoggedInError, OutgoingDocument


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
        with pytest.raises(NotLoggedInError):
            client.send_message(
                "5drr7us", "Test", [OutgoingDocument("a.pdf", "application/pdf", b"x", is_main=True)]
            )
        with pytest.raises(NotLoggedInError):
            client.find_box_live("some query")


def test_send_message_requires_exactly_one_main_document() -> None:
    with DatovkaClient(login=False) as client:
        client._logged_in = True
        with pytest.raises(ValueError, match="is_main"):
            client.send_message("5drr7us", "Test", [])
        with pytest.raises(ValueError, match="is_main"):
            client.send_message(
                "5drr7us",
                "Test",
                [
                    OutgoingDocument("a.pdf", "application/pdf", b"x", is_main=True),
                    OutgoingDocument("b.pdf", "application/pdf", b"y", is_main=True),
                ],
            )


def test_send_message_rejects_oversized_subject() -> None:
    with DatovkaClient(login=False) as client:
        client._logged_in = True
        with pytest.raises(ValueError, match="255"):
            client.send_message(
                "5drr7us",
                "x" * 256,
                [OutgoingDocument("a.pdf", "application/pdf", b"x", is_main=True)],
            )


def test_bad_login_raises_datovka_error() -> None:
    with DatovkaClient(login=False) as client:
        with pytest.raises(DatovkaError):
            client.login("baduser", "badpass")
