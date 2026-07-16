"""Plain data objects returned by :class:`datovka.client.DatovkaClient`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _timeval_to_datetime(sec: int, usec: int) -> datetime:
    return datetime.fromtimestamp(sec + usec / 1_000_000, tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class Envelope:
    """Summary fields of a message, as returned by list/get operations."""

    message_id: str
    sender_box_id: str | None
    sender_name: str | None
    recipient_box_id: str | None
    recipient_name: str | None
    subject: str | None
    delivery_time: datetime | None
    acceptance_time: datetime | None
    status: int | None
    attachment_size_kb: int | None
    message_type: str | None


@dataclass(frozen=True, slots=True)
class Document:
    """A single attachment/document within a message."""

    filename: str | None
    mime_type: str | None
    is_main: bool
    data: bytes


@dataclass(frozen=True, slots=True)
class Message:
    """A full message: envelope plus its documents."""

    envelope: Envelope
    documents: list[Document] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OutgoingDocument:
    """A document to attach to a message being sent.

    Distinct from :class:`Document` (which is read-only, populated from a
    message libdatovka gave us) to keep "what the library gives you" and
    "what you give the library" shapes explicit.
    """

    filename: str
    mime_type: str
    data: bytes
    is_main: bool = False
