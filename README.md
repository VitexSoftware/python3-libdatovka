# datovka

A Pythonic [ctypes](https://docs.python.org/3/library/ctypes.html) wrapper
around [libdatovka](https://gitlab.nic.cz/datovka/libdatovka), the C client
library for the Czech ISDS ("Datové schránky" / Data Box) system.

No compiled extension, no SWIG — this loads `libdatovka.so` at runtime and
exposes a small, high-level surface covering what a typical integration
needs: login, list messages, fetch a message with its attachments, mark as
read.

```python
from datovka import DatovkaClient

with DatovkaClient(url, username, password) as client:
    for envelope in client.list_received_messages(limit=10):
        print(envelope.message_id, envelope.subject, envelope.sender_name)

    message = client.get_received_message(envelope.message_id)
    for doc in message.documents:
        print(doc.filename, doc.mime_type, len(doc.data), "bytes")
```

## Requirements

- `libdatovka8` (the shared library) — see the
  [libdatovka packaging](https://github.com/Vitexus/libdatovka)
- Python >= 3.9

## Scope

This wraps a practical subset of libdatovka's ~166 `isds_*` functions, not
the full API: session lifecycle (`login`/`logout`/`ping`), listing received
and sent messages, fetching a full message with attachments, and marking a
message as read. The C structs it decodes (`isds_envelope`, `isds_message`,
`isds_document`, `isds_list`) are modelled field-for-field to match
`libdatovka/isds.h`; extending coverage to more `isds_*` calls means adding a
prototype in `datovka/_capi.py` and a thin method in `datovka/client.py`.

## License

LGPL-3.0-or-later, matching libdatovka.
