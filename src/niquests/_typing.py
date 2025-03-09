from __future__ import annotations

import typing
from http.cookiejar import CookieJar
from os import PathLike

from ._vendor.kiss_headers import Headers
from .auth import AsyncAuthBase, AuthBase
from .packages.urllib3 import AsyncResolverDescription, ResolverDescription, Retry, Timeout
from .packages.urllib3.contrib.resolver import BaseResolver
from .packages.urllib3.contrib.resolver._async import AsyncBaseResolver
from .packages.urllib3.fields import RequestField
from .structures import CaseInsensitiveDict

if typing.TYPE_CHECKING:
    from .models import PreparedRequest

#: (Restricted) list of http verb that we natively support and understand.
HttpMethodType: typing.TypeAlias = str
#: List of formats accepted for URL queries parameters. (e.g. /?param1=a&param2=b)
QueryParameterType: typing.TypeAlias = typing.Union[
    typing.List[typing.Tuple[str, typing.Union[str, typing.List[str], None]]],
    typing.Mapping[str, typing.Union[str, typing.List[str], None]],
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
    typing.Iterable[bytes],
    typing.Iterable[str],
]
AsyncBodyType: typing.TypeAlias = typing.Union[
    typing.AsyncIterable[bytes],
    typing.AsyncIterable[str],
]
#: HTTP Headers can be represented through three ways. 1) typical dict, 2) internal insensitive dict, and 3) list of tuple.
HeadersType: typing.TypeAlias = typing.Union[
    typing.MutableMapping[typing.Union[str, bytes], typing.Union[str, bytes]],
    typing.MutableMapping[str, str],
    typing.MutableMapping[bytes, bytes],
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
TLSVerifyType: typing.TypeAlias = typing.Union[bool, str, bytes, PathLike]
#: Accept a pem certificate (concat cert, key) or an explicit tuple of cert, key pair with an optional password.
TLSClientCertType: typing.TypeAlias = typing.Union[str, typing.Tuple[str, str], typing.Tuple[str, str, str]]
#: All accepted ways to describe desired timeout.
TimeoutType: typing.TypeAlias = typing.Union[
    int,  # TotalTimeout
    float,  # TotalTimeout
    typing.Tuple[typing.Union[int, float], typing.Union[int, float]],  # note: TotalTimeout, ConnectTimeout
    typing.Tuple[
        typing.Union[int, float], typing.Union[int, float], typing.Union[int, float]
    ],  # note: TotalTimeout, ConnectTimeout, ReadTimeout
    Timeout,
]
#: Specify (BasicAuth) authentication by passing a tuple of user, and password.
#: Can be a custom authentication mechanism that derive from AuthBase.
HttpAuthenticationType: typing.TypeAlias = typing.Union[
    typing.Tuple[typing.Union[str, bytes], typing.Union[str, bytes]],
    str,
    AuthBase,
    typing.Callable[["PreparedRequest"], "PreparedRequest"],
]
AsyncHttpAuthenticationType: typing.TypeAlias = typing.Union[
    AsyncAuthBase,
    typing.Callable[["PreparedRequest"], typing.Awaitable["PreparedRequest"]],
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

FieldSequenceType: typing.TypeAlias = typing.Sequence[typing.Union[typing.Tuple[str, FieldTupleType], RequestField]]
FieldsType: typing.TypeAlias = typing.Union[
    FieldSequenceType,
    typing.Mapping[str, FieldTupleType],
]

_HV = typing.TypeVar("_HV")

HookCallableType: typing.TypeAlias = typing.Callable[
    [_HV],
    typing.Optional[_HV],
]

HookType: typing.TypeAlias = typing.Dict[str, typing.List[HookCallableType[_HV]]]

AsyncHookCallableType: typing.TypeAlias = typing.Callable[
    [_HV],
    typing.Awaitable[typing.Optional[_HV]],
]

AsyncHookType: typing.TypeAlias = typing.Dict[str, typing.List[typing.Union[HookCallableType[_HV], AsyncHookCallableType[_HV]]]]

CacheLayerAltSvcType: typing.TypeAlias = typing.MutableMapping[typing.Tuple[str, int], typing.Optional[typing.Tuple[str, int]]]

RetryType: typing.TypeAlias = typing.Union[bool, int, Retry]

ResolverType: typing.TypeAlias = typing.Union[
    str,
    ResolverDescription,
    BaseResolver,
    typing.List[str],
    typing.List[ResolverDescription],
]

AsyncResolverType: typing.TypeAlias = typing.Union[
    str,
    AsyncResolverDescription,
    AsyncBaseResolver,
    typing.List[str],
    typing.List[AsyncResolverDescription],
]
