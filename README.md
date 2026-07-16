# datovka

![python3-libdatovka logo](debian/python3-libdatovka.svg)

A Pythonic [ctypes](https://docs.python.org/3/library/ctypes.html) wrapper
around [libdatovka](https://gitlab.nic.cz/datovka/libdatovka), the C client
library for the Czech ISDS ("Datové schránky" / Data Box) system.

No compiled extension, no SWIG — this loads `libdatovka.so` at runtime and
exposes a small, high-level surface covering what a typical integration
needs: login, list messages, fetch a message with its attachments, mark as
read, send a new message, and look up a recipient's data box ID.

```python
from datovka import DatovkaClient, OutgoingDocument

with DatovkaClient(url, username, password) as client:
    for envelope in client.list_received_messages(limit=10):
        print(envelope.message_id, envelope.subject, envelope.sender_name)

    message = client.get_received_message(envelope.message_id)
    for doc in message.documents:
        print(doc.filename, doc.mime_type, len(doc.data), "bytes")

    # Sending a new message needs exactly one is_main=True document.
    with open("smlouva.pdf", "rb") as f:
        pdf_bytes = f.read()
    client.send_message(
        "5drr7us",
        "Smlouva k podpisu",
        [OutgoingDocument("smlouva.pdf", "application/pdf", pdf_bytes, is_main=True)],
    )

    # Live search is rate-limited; prefer an offline directory (e.g. the
    # seznamds package) for routine lookups and use this as a fallback.
    for box in client.find_box_live("Firma s.r.o."):
        print(box["box_id"], box["name"])
```

## Requirements

- `libdatovka8` (the shared library) — see the
  [libdatovka packaging](https://github.com/Vitexus/libdatovka)
- Python >= 3.9

## Scope

This wraps a practical subset of libdatovka's ~166 `isds_*` functions, not
the full API: session lifecycle (`login`/`logout`/`ping`), listing received
and sent messages, fetching a full message with attachments, marking a
message as read, sending a new message with attachments
(`send_message`), and recipient lookup via the live fulltext search
(`find_box_live`). The C structs it decodes (`isds_envelope`,
`isds_message`, `isds_document`, `isds_list`, `isds_fulltext_result`) are
modelled field-for-field to match `libdatovka/isds.h`; extending coverage to
more `isds_*` calls means adding a prototype in `datovka/_capi.py` and a
thin method in `datovka/client.py`.

## License

LGPL-3.0-or-later, matching libdatovka.
