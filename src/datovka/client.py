"""High-level, Pythonic client for the Czech ISDS Data Box system.

Wraps libdatovka's isds_* C API via ctypes. See ``datovka._capi`` for the raw
bindings.
"""

from __future__ import annotations

import ctypes
from ctypes import POINTER, byref, c_ulong, cast
from types import TracebackType

from . import _capi
from .exceptions import DatovkaError, NotLoggedInError
from .models import Document, Envelope, Message, OutgoingDocument, _timeval_to_datetime

MAX_SUBJECT_LENGTH = 255
"""ISDS caps dmAnnotation (the message subject) at 255 characters."""

DEFAULT_URL = "https://ws1.mojedatovaschranka.cz/"
"""Production ISDS endpoint. Use a test/sandbox URL for development.

Trailing slash is required: libdatovka appends its SOAP service paths
(e.g. "DS/dz") directly onto this string with no separator.
"""

_INIT_REFCOUNT = 0


def _isds_init_once() -> None:
    global _INIT_REFCOUNT
    if _INIT_REFCOUNT == 0:
        _check(None, _capi.lib.isds_init(), "isds_init failed")
    _INIT_REFCOUNT += 1


def _isds_cleanup_once() -> None:
    global _INIT_REFCOUNT
    _INIT_REFCOUNT -= 1
    if _INIT_REFCOUNT <= 0:
        _INIT_REFCOUNT = 0
        _capi.lib.isds_cleanup()


def _check(ctx: ctypes.c_void_p | int | None, code: int, fallback_message: str) -> None:
    if code == _capi.IE_SUCCESS:
        return
    message = _capi.lib.isds_strerror(code)
    message_str = message.decode("utf-8", "replace") if message else fallback_message
    detail = None
    if ctx:
        detail_raw = _capi.lib.isds_long_message(ctx)
        detail = detail_raw.decode("utf-8", "replace") if detail_raw else None
    error_cls = NotLoggedInError if code == _capi.IE_NOT_LOGGED_IN else DatovkaError
    raise error_cls(code, message_str, detail)


def _decode(value: bytes | None) -> str | None:
    return value.decode("utf-8", "replace") if value is not None else None


def _deref(ptr) -> int | bool | None:  # noqa: ANN001 - ctypes pointer, no clean annotation
    """Dereference a ctypes optional-value pointer, or return None if NULL."""
    if not ptr:
        return None
    return ptr.contents.value


def _envelope_from_struct(struct_ptr, message_id_fallback: str | None = None) -> Envelope:  # noqa: ANN001
    env = struct_ptr.contents
    delivery = None
    if env.dmDeliveryTime:
        tv = env.dmDeliveryTime.contents
        delivery = _timeval_to_datetime(tv.tv_sec, tv.tv_usec)
    acceptance = None
    if env.dmAcceptanceTime:
        tv = env.dmAcceptanceTime.contents
        acceptance = _timeval_to_datetime(tv.tv_sec, tv.tv_usec)
    return Envelope(
        message_id=_decode(env.dmID) or message_id_fallback or "",
        sender_box_id=_decode(env.dbIDSender),
        sender_name=_decode(env.dmSender),
        recipient_box_id=_decode(env.dbIDRecipient),
        recipient_name=_decode(env.dmRecipient),
        subject=_decode(env.dmAnnotation),
        delivery_time=delivery,
        acceptance_time=acceptance,
        status=_deref(env.dmMessageStatus),
        attachment_size_kb=_deref(env.dmAttachmentSize),
        message_type=_decode(env.dmType),
    )


def _iter_isds_list(list_ptr, element_type):  # noqa: ANN001
    """Iterate an isds_list*, yielding each node's ``data`` cast to element_type."""
    node = list_ptr
    while node:
        data_ptr = cast(node.contents.data, POINTER(element_type))
        if data_ptr:
            yield data_ptr
        node = node.contents.next


def _build_isds_list(items: list) -> list[_capi.IsdsList]:  # noqa: ANN001
    """Chain a list of ctypes structs into a linked isds_list.

    Returns the list of node structures (empty if ``items`` is empty);
    ``nodes[0]`` is the head to pass to the C API. The caller must keep the
    returned list (and ``items``) alive for as long as the C function using
    them is running -- these are Python/ctypes-owned structures, never
    passed to isds_*_free.
    """
    nodes = [_capi.IsdsList() for _ in items]
    for i, (node, item) in enumerate(zip(nodes, items)):
        node.data = cast(byref(item), ctypes.c_void_p)
        node.destructor = None
        node.next = cast(byref(nodes[i + 1]), POINTER(_capi.IsdsList)) if i + 1 < len(nodes) else None
    return nodes


class DatovkaClient:
    """A logged-in ISDS session.

    Usage::

        with DatovkaClient(url, username, password) as client:
            for envelope in client.list_received_messages():
                print(envelope.subject)

    Not thread-safe: each ``DatovkaClient`` wraps one libdatovka context,
    which is not safe to share across threads.
    """

    def __init__(
        self,
        url: str = DEFAULT_URL,
        username: str | None = None,
        password: str | None = None,
        *,
        login: bool = True,
    ) -> None:
        _isds_init_once()
        self._ctx = _capi.lib.isds_ctx_create()
        if not self._ctx:
            _isds_cleanup_once()
            raise DatovkaError(_capi.IE_NOMEM, "isds_ctx_create returned NULL")
        self._logged_in = False
        self._url = url
        if login and username and password:
            self.login(username, password)

    def login(self, username: str, password: str, url: str | None = None) -> None:
        """Authenticate with a username and password (no client certificate)."""
        target_url = (url or self._url).encode("utf-8")
        code = _capi.lib.isds_login(
            self._ctx,
            target_url,
            username.encode("utf-8"),
            password.encode("utf-8"),
            None,
            None,
        )
        _check(self._ctx, code, "isds_login failed")
        self._logged_in = True

    def logout(self) -> None:
        if not self._logged_in:
            return
        code = _capi.lib.isds_logout(self._ctx)
        self._logged_in = False
        _check(self._ctx, code, "isds_logout failed")

    def ping(self) -> None:
        """Verify the connection is alive; raises DatovkaError if not."""
        _check(self._ctx, _capi.lib.isds_ping(self._ctx), "isds_ping failed")

    def _require_login(self) -> None:
        if not self._logged_in:
            raise NotLoggedInError(_capi.IE_NOT_LOGGED_IN, "not logged in")

    def _list_messages(self, fn, limit: int | None) -> list[Envelope]:  # noqa: ANN001
        self._require_login()
        messages_head = POINTER(_capi.IsdsList)()
        number = c_ulong(limit or 0)
        code = fn(
            self._ctx,
            None,
            None,
            None,
            _capi.MESSAGESTATE_ANY,
            0,
            byref(number),
            byref(messages_head),
        )
        try:
            _check(self._ctx, code, "failed to list messages")
            return [
                _envelope_from_struct(msg.contents.envelope)
                for msg in _iter_isds_list(messages_head, _capi.IsdsMessage)
            ]
        finally:
            if messages_head:
                _capi.lib.isds_list_free(byref(messages_head))

    def list_received_messages(self, limit: int | None = None) -> list[Envelope]:
        """Return envelopes (summaries) of received messages, newest activity first."""
        return self._list_messages(_capi.lib.isds_get_list_of_received_messages, limit)

    def list_sent_messages(self, limit: int | None = None) -> list[Envelope]:
        """Return envelopes (summaries) of sent messages."""
        return self._list_messages(_capi.lib.isds_get_list_of_sent_messages, limit)

    def get_received_message(self, message_id: str) -> Message:
        """Fetch a received message in full, including its documents/attachments."""
        self._require_login()
        message_ptr = POINTER(_capi.IsdsMessage)()
        code = _capi.lib.isds_get_received_message(
            self._ctx, message_id.encode("utf-8"), byref(message_ptr)
        )
        try:
            _check(self._ctx, code, "failed to fetch message")
            return self._message_from_struct(message_ptr, message_id)
        finally:
            if message_ptr:
                _capi.lib.isds_message_free(byref(message_ptr))

    def _message_from_struct(self, message_ptr, message_id: str) -> Message:  # noqa: ANN001
        msg = message_ptr.contents
        envelope = _envelope_from_struct(msg.envelope, message_id_fallback=message_id)
        documents: list[Document] = []
        for doc_ptr in _iter_isds_list(msg.documents, _capi.IsdsDocument):
            doc = doc_ptr.contents
            data = b""
            if not doc.is_xml and doc.data and doc.data_length:
                data = ctypes.string_at(doc.data, doc.data_length)
            documents.append(
                Document(
                    filename=_decode(doc.dmFileDescr),
                    mime_type=_decode(doc.dmMimeType),
                    is_main=(doc.dmFileMetaType == _capi.FILEMETATYPE_MAIN),
                    data=data,
                )
            )
        return Message(envelope=envelope, documents=documents)

    def mark_as_read(self, message_id: str) -> None:
        self._require_login()
        code = _capi.lib.isds_mark_message_read(self._ctx, message_id.encode("utf-8"))
        _check(self._ctx, code, "failed to mark message as read")

    def send_message(
        self,
        recipient_box_id: str,
        subject: str,
        documents: list[OutgoingDocument],
        *,
        recipient_org_unit: str | None = None,
        sender_ref_number: str | None = None,
    ) -> None:
        """Send a new message to a data box.

        ``documents`` must contain exactly one document with ``is_main=True``
        (the ISDS API's own requirement); any others are sent as enclosures.
        Total attachment size is capped by ISDS at 50 MB.
        """
        self._require_login()
        if len(subject) > MAX_SUBJECT_LENGTH:
            raise ValueError(
                f"subject is {len(subject)} characters, ISDS caps it at {MAX_SUBJECT_LENGTH}"
            )
        main_count = sum(1 for d in documents if d.is_main)
        if main_count != 1:
            raise ValueError(
                f"documents must contain exactly one is_main=True entry, got {main_count}"
            )

        # Keep every ctypes-owned object referenced until after the call:
        # C structures don't participate in Python's refcounting, so nothing
        # here may be allowed to become garbage before isds_send_message runs.
        buffers = [ctypes.create_string_buffer(d.data, len(d.data)) for d in documents]
        doc_structs = [_capi.IsdsDocument() for _ in documents]
        for doc_struct, doc, buf in zip(doc_structs, documents, buffers):
            doc_struct.is_xml = False
            doc_struct.data = cast(buf, ctypes.c_void_p)
            doc_struct.data_length = len(doc.data)
            doc_struct.dmMimeType = doc.mime_type.encode("utf-8")
            doc_struct.dmFileMetaType = (
                _capi.FILEMETATYPE_MAIN if doc.is_main else _capi.FILEMETATYPE_ENCLOSURE
            )
            doc_struct.dmFileDescr = doc.filename.encode("utf-8")
        list_nodes = _build_isds_list(doc_structs)

        envelope = _capi.IsdsEnvelope()
        envelope.dbIDRecipient = recipient_box_id.encode("utf-8")
        envelope.dmAnnotation = subject.encode("utf-8")
        if recipient_org_unit is not None:
            envelope.dmRecipientOrgUnit = recipient_org_unit.encode("utf-8")
        if sender_ref_number is not None:
            envelope.dmSenderRefNumber = sender_ref_number.encode("utf-8")

        message = _capi.IsdsMessage()
        message.envelope = cast(byref(envelope), POINTER(_capi.IsdsEnvelope))
        message.documents = (
            cast(byref(list_nodes[0]), POINTER(_capi.IsdsList)) if list_nodes else None
        )

        code = _capi.lib.isds_send_message(self._ctx, byref(message))
        # No isds_message_free here: `message` is Python/ctypes-owned, not
        # something the library allocated for us to free.
        _check(self._ctx, code, "failed to send message")

    def find_box_live(self, query: str, limit: int = 10) -> list[dict]:
        """Look up data boxes by name/IČO/address via the live ISDS search.

        This calls the rate-limited SOAP API directly. Prefer an offline
        directory (e.g. the ``seznamds`` package) for routine lookups; use
        this only as a fallback.
        """
        self._require_login()
        boxes_head = POINTER(_capi.IsdsList)()
        page_size = c_ulong(limit)
        code = _capi.lib.isds_find_box_by_fulltext(
            self._ctx,
            query.encode("utf-8"),
            None,  # target: search all fields
            None,  # box_type: any
            byref(page_size),
            None,
            None,
            None,
            None,
            None,
            None,
            byref(boxes_head),
        )
        try:
            _check(self._ctx, code, "failed to search for data boxes")
            return [
                {
                    "box_id": _decode(box.contents.dbID),
                    "type": box.contents.dbType,
                    "name": _decode(box.contents.name),
                    "address": _decode(box.contents.address),
                }
                for box in _iter_isds_list(boxes_head, _capi.IsdsFulltextResult)
            ]
        finally:
            if boxes_head:
                _capi.lib.isds_list_free(byref(boxes_head))

    def close(self) -> None:
        if self._ctx:
            if self._logged_in:
                try:
                    self.logout()
                except DatovkaError:
                    pass
            ctx = ctypes.c_void_p(self._ctx)
            _capi.lib.isds_ctx_free(byref(ctx))
            self._ctx = None
            _isds_cleanup_once()

    def __enter__(self) -> DatovkaClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
