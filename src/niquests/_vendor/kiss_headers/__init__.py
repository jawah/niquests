"""
Kiss-Headers
~~~~~~~~~~~~~~

Kiss-Headers is a headers, HTTP or IMAP4 _(message, email)_ flavour, utility, written in pure Python, for humans.
Object oriented headers. Keep it sweet and simple.
Basic usage:

   >>> import requests
   >>> from kiss_headers import parse_it
   >>> r = requests.get('https://www.python.org')
   >>> headers = parse_it(r)
   >>> 'charset' in headers.content_type
   True
   >>> headers.content_type.charset
   'utf-8'
   >>> 'text/html' in headers.content_type
   True
   >>> headers.content_type == 'text/html'
   True
   >>> headers -= 'content-type'
   >>> 'Content-Type' in headers
   False

... or from a raw IMAP4 message:

   >>> message = requests.get("https://gist.githubusercontent.com/Ousret/8b84b736c375bb6aa3d389e86b5116ec/raw/21cb2f7af865e401c37d9b053fb6fe1abf63165b/sample-message.eml").content
   >>> headers = parse_it(message)
   >>> 'Sender' in headers
   True

Others methods and usages are available - see the full documentation
at <https://github.com/jawah/kiss-headers>.

:copyright: (c) 2020 by Ahmed TAHRI
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

from .api import dumps, explain, get_polymorphic, parse_it
from .builder import (
    Accept,
    AcceptEncoding,
    AcceptLanguage,
    Allow,
    AltSvc,
    Authorization,
    BasicAuthorization,
    CacheControl,
    Connection,
    ContentDisposition,
    ContentEncoding,
    ContentLength,
    ContentRange,
    ContentSecurityPolicy,
    ContentType,
    CrossOriginResourcePolicy,
    CustomHeader,
    Date,
    Digest,
    Dnt,
    Etag,
    Expires,
    Forwarded,
    From,
    Host,
    IfMatch,
    IfModifiedSince,
    IfNoneMatch,
    IfUnmodifiedSince,
    KeepAlive,
    LastModified,
    Location,
    ProxyAuthorization,
    Referer,
    ReferrerPolicy,
    RetryAfter,
    Server,
    SetCookie,
    StrictTransportSecurity,
    TransferEncoding,
    UpgradeInsecureRequests,
    UserAgent,
    Vary,
    WwwAuthenticate,
    XContentTypeOptions,
    XDnsPrefetchControl,
    XFrameOptions,
    XXssProtection,
)
from .models import Attributes, Header, Headers, lock_output_type
from .serializer import decode, encode
from .version import VERSION, __version__

__all__ = (
    "dumps",
    "explain",
    "get_polymorphic",
    "parse_it",
    "Attributes",
    "Header",
    "Headers",
    "lock_output_type",
    "decode",
    "encode",
    "VERSION",
    "__version__",
    "Accept",
    "AcceptEncoding",
    "AcceptLanguage",
    "Allow",
    "AltSvc",
    "Authorization",
    "BasicAuthorization",
    "CacheControl",
    "Connection",
    "ContentDisposition",
    "ContentEncoding",
    "ContentLength",
    "ContentRange",
    "ContentSecurityPolicy",
    "ContentType",
    "CrossOriginResourcePolicy",
    "CustomHeader",
    "Date",
    "Digest",
    "Dnt",
    "Etag",
    "Expires",
    "Forwarded",
    "From",
    "Host",
    "IfMatch",
    "IfModifiedSince",
    "IfNoneMatch",
    "IfUnmodifiedSince",
    "KeepAlive",
    "LastModified",
    "Location",
    "ProxyAuthorization",
    "Referer",
    "ReferrerPolicy",
    "RetryAfter",
    "Server",
    "SetCookie",
    "StrictTransportSecurity",
    "TransferEncoding",
    "UpgradeInsecureRequests",
    "UserAgent",
    "Vary",
    "WwwAuthenticate",
    "XContentTypeOptions",
    "XDnsPrefetchControl",
    "XFrameOptions",
    "XXssProtection",
)
