from __future__ import annotations

import typing
from http.cookiejar import CookieJar

from kiss_headers import Headers
from urllib3 import Retry, Timeout
from urllib3.fields import RequestField

from .auth import AuthBase
from .structures import CaseInsensitiveDict

#: (Restricted) list of http verb that we natively support and understand.
HttpMethodType: typing.TypeAlias = (
    str  # todo: have typing.Literal when ready to drop Python 3.7
)
#: List of formats accepted for URL queries parameters. (e.g. /?param1=a&param2=b)
QueryParameterType: typing.TypeAlias = typing.Union[
    typing.List[typing.Tuple[str, str]],
    typing.Mapping[str, str],
    bytes,
    str,
]
BodyFormType: typing.TypeAlias = typing.Union[
    typing.List[typing.Tuple[str, str]],
    typing.Dict[str, typing.Union[typing.List[str], str]],
]
#: Accepted types for the payload in POST, PUT, and PATCH requests.
BodyType: typing.TypeAlias = typing.Union[
    str,
    bytes,
    bytearray,
    typing.IO,
    BodyFormType,
]
#: HTTP Headers can be represented through three ways. 1) typical dict, 2) internal insensitive dict, and 3) list of tuple.
HeadersType: typing.TypeAlias = typing.Union[
    typing.MutableMapping[typing.Union[str, bytes], typing.Union[str, bytes]],
    CaseInsensitiveDict,
    typing.List[typing.Tuple[typing.Union[str, bytes], typing.Union[str, bytes]]],
    Headers,
]
#: We accept both typical mapping and stdlib CookieJar.
CookiesType: typing.TypeAlias = typing.Union[
    typing.MutableMapping[str, str],
    CookieJar,
]
#: Either Yes/No, or CA bundle pem location. Or directly the raw bundle content itself.
TLSVerifyType: typing.TypeAlias = typing.Union[bool, str, bytes]
#: Accept a pem certificate (concat cert, key) or an explicit tuple of cert, key pair with an optional password.
TLSClientCertType: typing.TypeAlias = typing.Union[
    str, typing.Tuple[str, str], typing.Tuple[str, str, str]
]
#: All accepted ways to describe desired timeout.
TimeoutType: typing.TypeAlias = typing.Union[
    int,  # TotalTimeout
    float,  # TotalTimeout
    typing.Tuple[
        typing.Union[int, float], typing.Union[int, float]
    ],  # note: TotalTimeout, ConnectTimeout
    typing.Tuple[
        typing.Union[int, float], typing.Union[int, float], typing.Union[int, float]
    ],  # note: TotalTimeout, ConnectTimeout, ReadTimeout
    Timeout,
]
#: Specify (BasicAuth) authentication by passing a tuple of user, and password.
#: Can be a custom authentication mechanism that derive from AuthBase.
HttpAuthenticationType: typing.TypeAlias = typing.Union[
    typing.Tuple[typing.Union[str, bytes], typing.Union[str, bytes]],
    AuthBase,
]
#: Map for each protocol (http, https) associated proxy to be used.
ProxyType: typing.TypeAlias = typing.Dict[str, str]

# cases:
#   1) fn, fp
#   2) fn, fp, ft
#   3) fn, fp, ft, fh
# OR
#   4) fp
BodyFileType: typing.TypeAlias = typing.Union[
    str,
    bytes,
    bytearray,
    typing.IO,
]
MultiPartFileType: typing.TypeAlias = typing.Tuple[
    str,
    typing.Union[
        BodyFileType,
        typing.Tuple[str, BodyFileType],
        typing.Tuple[str, BodyFileType, str],
        typing.Tuple[str, BodyFileType, str, HeadersType],
    ],
]
MultiPartFilesType: typing.TypeAlias = typing.List[MultiPartFileType]
#: files (multipart formdata) can be (also) passed as dict.
MultiPartFilesAltType: typing.TypeAlias = typing.Dict[
    str,
    typing.Union[
        BodyFileType,
        typing.Tuple[str, BodyFileType],
        typing.Tuple[str, BodyFileType, str],
        typing.Tuple[str, BodyFileType, str, HeadersType],
    ],
]

FieldValueType: typing.TypeAlias = typing.Union[str, bytes]
FieldTupleType: typing.TypeAlias = typing.Union[
    FieldValueType,
    typing.Tuple[str, FieldValueType],
    typing.Tuple[str, FieldValueType, str],
]

FieldSequenceType: typing.TypeAlias = typing.Sequence[
    typing.Union[typing.Tuple[str, FieldTupleType], RequestField]
]
FieldsType: typing.TypeAlias = typing.Union[
    FieldSequenceType,
    typing.Mapping[str, FieldTupleType],
]

_HV = typing.TypeVar("_HV")

HookCallableType: typing.TypeAlias = typing.Callable[
    [
        _HV,
    ],
    typing.Optional[_HV],
]

HookType: typing.TypeAlias = typing.Dict[str, typing.List[HookCallableType[_HV]]]

CacheLayerAltSvcType: typing.TypeAlias = typing.MutableMapping[
    typing.Tuple[str, int], typing.Optional[typing.Tuple[str, int]]
]

RetryType: typing.TypeAlias = typing.Union[bool, int, Retry]
