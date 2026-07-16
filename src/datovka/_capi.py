"""Raw ctypes bindings for libdatovka's isds_* C API.

Struct layouts mirror ``libdatovka/isds.h`` field-for-field and in
declaration order, since ctypes needs the full, correctly ordered layout to
compute member offsets correctly -- even for fields this wrapper never reads.
Fields the high-level client doesn't use are typed as ``c_void_p`` (still
correct size on every field width the C header uses: a pointer), rather than
modelled in full, to keep this file from growing without bound.

Only the header's own field ordering is load-bearing here; do not reorder.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import (
    POINTER,
    Structure,
    c_bool,
    c_char_p,
    c_int,
    c_int32,
    c_int64,
    c_long,
    c_size_t,
    c_uint,
    c_ulong,
    c_void_p,
)


def _load_library() -> ctypes.CDLL:
    for candidate in ("libdatovka.so.8", "libdatovka.so", ctypes.util.find_library("datovka")):
        if not candidate:
            continue
        try:
            return ctypes.CDLL(candidate)
        except OSError:
            continue
    raise OSError(
        "Could not load libdatovka. Install the libdatovka8 package "
        "(https://gitlab.nic.cz/datovka/libdatovka)."
    )


lib = _load_library()

# isds_error enum values (see isds.h)
IE_SUCCESS = 0
IE_ERROR = 1
IE_NOTSUP = 2
IE_INVAL = 3
IE_INVALID_CONTEXT = 4
IE_NOT_LOGGED_IN = 5
IE_CONNECTION_CLOSED = 6
IE_TIMED_OUT = 7
IE_NONEXIST = 8
IE_NOMEM = 9
IE_NETWORK = 10
IE_HTTP = 11
IE_SOAP = 12
IE_XML = 13
IE_ISDS = 14
IE_ENUM = 15
IE_DATE = 16
IE_TOO_BIG = 17
IE_TOO_SMALL = 18
IE_NOTUNIQ = 19
IE_NOTEQUAL = 20
IE_PARTIAL_SUCCESS = 21
IE_ABORTED = 22
IE_SECURITY = 23

MESSAGESTATE_ANY = 0x7FE

# isds_FileMetaType enum
FILEMETATYPE_MAIN = 0
FILEMETATYPE_ENCLOSURE = 1
FILEMETATYPE_SIGNATURE = 2
FILEMETATYPE_META = 3

# isds_fulltext_target enum (search field for isds_find_box_by_fulltext)
FULLTEXT_ALL = 0
FULLTEXT_ADDRESS = 1
FULLTEXT_IC = 2
FULLTEXT_BOX_ID = 3


class IsdsTimeval(Structure):
    _fields_ = [
        ("tv_sec", c_int64),
        ("tv_usec", c_int32),
    ]


class IsdsList(Structure):
    pass


IsdsList._fields_ = [
    ("next", POINTER(IsdsList)),
    ("data", c_void_p),
    ("destructor", c_void_p),
]


class IsdsEnvelope(Structure):
    _fields_ = [
        ("dmID", c_char_p),
        ("dbIDSender", c_char_p),
        ("dmSender", c_char_p),
        ("dmSenderAddress", c_char_p),
        ("dmSenderType", POINTER(c_long)),
        ("dmRecipient", c_char_p),
        ("dmRecipientAddress", c_char_p),
        ("dmAmbiguousRecipient", POINTER(c_bool)),
        ("dmOrdinal", POINTER(c_ulong)),
        ("dmMessageStatus", POINTER(c_int)),
        ("dmAttachmentSize", POINTER(c_long)),
        ("dmDeliveryTime", POINTER(IsdsTimeval)),
        ("dmAcceptanceTime", POINTER(IsdsTimeval)),
        ("hash", c_void_p),
        ("timestamp", c_void_p),
        ("timestamp_length", c_size_t),
        ("events", c_void_p),
        ("dmSenderOrgUnit", c_char_p),
        ("dmSenderOrgUnitNum", POINTER(c_long)),
        ("dbIDRecipient", c_char_p),
        ("dmRecipientOrgUnit", c_char_p),
        ("dmRecipientOrgUnitNum", POINTER(c_long)),
        ("dmToHands", c_char_p),
        ("dmAnnotation", c_char_p),
        ("dmRecipientRefNumber", c_char_p),
        ("dmSenderRefNumber", c_char_p),
        ("dmRecipientIdent", c_char_p),
        ("dmSenderIdent", c_char_p),
        ("dmLegalTitleLaw", POINTER(c_long)),
        ("dmLegalTitleYear", POINTER(c_long)),
        ("dmLegalTitleSect", c_char_p),
        ("dmLegalTitlePar", c_char_p),
        ("dmLegalTitlePoint", c_char_p),
        ("dmPersonalDelivery", POINTER(c_bool)),
        ("dmAllowSubstDelivery", POINTER(c_bool)),
        ("dmType", c_char_p),
        ("dmVODZ", POINTER(c_bool)),
        ("attsNum", POINTER(c_long)),
        ("dmOVM", POINTER(c_bool)),
        ("dmPublishOwnID", POINTER(c_bool)),
        ("idLevel", POINTER(c_int)),
    ]


class IsdsDocument(Structure):
    _fields_ = [
        ("is_xml", c_bool),
        ("xml_node_list", c_void_p),
        ("data", c_void_p),
        ("data_length", c_size_t),
        ("dmMimeType", c_char_p),
        ("dmFileMetaType", c_int),
        ("dmFileGuid", c_char_p),
        ("dmUpFileGuid", c_char_p),
        ("dmFileDescr", c_char_p),
        ("dmFormat", c_char_p),
    ]


class IsdsMessage(Structure):
    _fields_ = [
        ("raw", c_void_p),
        ("raw_length", c_size_t),
        ("raw_type", c_int),
        ("xml", c_void_p),
        ("envelope", POINTER(IsdsEnvelope)),
        ("documents", POINTER(IsdsList)),
        ("ext_files", c_void_p),
    ]


class IsdsFulltextResult(Structure):
    _fields_ = [
        ("dbID", c_char_p),
        ("dbType", c_int),
        ("name", c_char_p),
        ("name_match_start", c_void_p),
        ("name_match_end", c_void_p),
        ("address", c_char_p),
        ("address_match_start", c_void_p),
        ("address_match_end", c_void_p),
    ]


# --- Function prototypes -----------------------------------------------

lib.isds_init.argtypes = []
lib.isds_init.restype = c_int

lib.isds_cleanup.argtypes = []
lib.isds_cleanup.restype = c_int

lib.isds_ctx_create.argtypes = []
lib.isds_ctx_create.restype = c_void_p

lib.isds_ctx_free.argtypes = [POINTER(c_void_p)]
lib.isds_ctx_free.restype = c_int

lib.isds_login.argtypes = [
    c_void_p,  # context
    c_char_p,  # url
    c_char_p,  # username
    c_char_p,  # password
    c_void_p,  # pki_credentials
    c_void_p,  # otp
]
lib.isds_login.restype = c_int

lib.isds_logout.argtypes = [c_void_p]
lib.isds_logout.restype = c_int

lib.isds_ping.argtypes = [c_void_p]
lib.isds_ping.restype = c_int

lib.isds_get_list_of_received_messages.argtypes = [
    c_void_p,
    POINTER(IsdsTimeval),
    POINTER(IsdsTimeval),
    POINTER(c_long),
    c_uint,
    c_ulong,
    POINTER(c_ulong),
    POINTER(POINTER(IsdsList)),
]
lib.isds_get_list_of_received_messages.restype = c_int

lib.isds_get_list_of_sent_messages.argtypes = [
    c_void_p,
    POINTER(IsdsTimeval),
    POINTER(IsdsTimeval),
    POINTER(c_long),
    c_uint,
    c_ulong,
    POINTER(c_ulong),
    POINTER(POINTER(IsdsList)),
]
lib.isds_get_list_of_sent_messages.restype = c_int

lib.isds_get_received_message.argtypes = [
    c_void_p,
    c_char_p,
    POINTER(POINTER(IsdsMessage)),
]
lib.isds_get_received_message.restype = c_int

lib.isds_get_signed_sent_message.argtypes = [
    c_void_p,
    c_char_p,
    POINTER(POINTER(IsdsMessage)),
]
lib.isds_get_signed_sent_message.restype = c_int

lib.isds_mark_message_read.argtypes = [c_void_p, c_char_p]
lib.isds_mark_message_read.restype = c_int

lib.isds_send_message.argtypes = [c_void_p, POINTER(IsdsMessage)]
lib.isds_send_message.restype = c_int

lib.isds_find_box_by_fulltext.argtypes = [
    c_void_p,
    c_char_p,  # query
    POINTER(c_int),  # target (isds_fulltext_target*)
    POINTER(c_int),  # box_type (isds_DbType*)
    POINTER(c_ulong),  # page_size
    POINTER(c_ulong),  # page_number
    POINTER(c_bool),  # track_matches
    POINTER(POINTER(c_ulong)),  # total_matching_boxes
    POINTER(POINTER(c_ulong)),  # current_page_beginning
    POINTER(POINTER(c_ulong)),  # current_page_size
    POINTER(POINTER(c_bool)),  # last_page
    POINTER(POINTER(IsdsList)),  # boxes
]
lib.isds_find_box_by_fulltext.restype = c_int

lib.isds_message_free.argtypes = [POINTER(POINTER(IsdsMessage))]
lib.isds_message_free.restype = None

lib.isds_list_free.argtypes = [POINTER(POINTER(IsdsList))]
lib.isds_list_free.restype = None

lib.isds_fulltext_result_free.argtypes = [POINTER(POINTER(IsdsFulltextResult))]
lib.isds_fulltext_result_free.restype = None

lib.isds_strerror.argtypes = [c_int]
lib.isds_strerror.restype = c_char_p

lib.isds_long_message.argtypes = [c_void_p]
lib.isds_long_message.restype = c_char_p
