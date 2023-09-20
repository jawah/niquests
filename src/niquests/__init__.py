#   __
#  /__)  _  _     _   _ _/   _
# / (   (- (/ (/ (- _)  /  _)
#          /

"""
Niquests HTTP Library
~~~~~~~~~~~~~~~~~~~~~

Niquests is an HTTP library, written in Python, for human beings.
Basic GET usage:

   >>> import niquests
   >>> r = niquests.get('https://www.python.org')
   >>> r.status_code
   200
   >>> b'Python is a programming language' in r.content
   True

... or POST:

   >>> payload = dict(key1='value1', key2='value2')
   >>> r = niquests.post('https://httpbin.org/post', data=payload)
   >>> print(r.text)
   {
     ...
     "form": {
       "key1": "value1",
       "key2": "value2"
     },
     ...
   }

The other HTTP methods are supported - see `requests.api`. Full documentation
is at <https://niquests.readthedocs.io>.

:copyright: (c) 2017 by Kenneth Reitz.
:license: Apache 2.0, see LICENSE for more details.
"""

import warnings

import urllib3
from charset_normalizer import __version__ as charset_normalizer_version

from .exceptions import RequestsDependencyWarning


def check_compatibility(urllib3_version, charset_normalizer_version) -> None:
    urllib3_version = urllib3_version.split(".")
    assert urllib3_version != ["dev"]  # Verify urllib3 isn't installed from git.

    # Sometimes, urllib3 only reports its version as 16.1.
    if len(urllib3_version) == 2:
        urllib3_version.append("0")

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version  # noqa: F811
    major, minor, patch = int(major), int(minor), int(patch)
    # urllib3 >= 2.0.9xx
    assert major >= 2
    assert patch >= 900

    # Check charset_normalizer for compatibility.
    major, minor, patch = charset_normalizer_version.split(".")[:3]
    major, minor, patch = int(major), int(minor), int(patch)
    # charset_normalizer >= 2.0.0 < 4.0.0
    assert (2, 0, 0) <= (major, minor, patch) < (4, 0, 0)


def _check_cryptography(cryptography_version) -> None:
    # cryptography < 1.3.4
    try:
        cryptography_version = list(map(int, cryptography_version.split(".")))
    except ValueError:
        return

    if cryptography_version < [1, 3, 4]:
        warning = "Old version of cryptography ({}) may cause slowdown.".format(
            cryptography_version
        )
        warnings.warn(warning, RequestsDependencyWarning)


# Check imported dependencies for compatibility.
try:
    check_compatibility(urllib3.__version__, charset_normalizer_version)
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or charset_normalizer ({}) doesn't match a supported "
        "version!".format(urllib3.__version__, charset_normalizer_version),
        RequestsDependencyWarning,
    )

# Attempt to enable urllib3's fallback for SNI support
# if the standard library doesn't support SNI or the
# 'ssl' library isn't available.
try:
    try:
        import ssl
    except ImportError:
        ssl = None  # type: ignore[assignment]

    if not getattr(ssl, "HAS_SNI", False):
        from urllib3.contrib import pyopenssl

        pyopenssl.inject_into_urllib3()

        # Check cryptography version
        from cryptography import __version__ as cryptography_version

        _check_cryptography(cryptography_version)
except ImportError:
    pass

# urllib3's DependencyWarnings should be silenced.
from urllib3.exceptions import DependencyWarning

warnings.simplefilter("ignore", DependencyWarning)

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

from . import utils
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
from .api import delete, get, head, options, patch, post, put, request
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response
from .sessions import Session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

# FileModeWarnings go off per the default.
warnings.simplefilter("default", FileModeWarning, append=True)


__all__ = (
    "RequestsDependencyWarning",
    "utils",
    "__author__",
    "__author_email__",
    "__build__",
    "__cake__",
    "__copyright__",
    "__description__",
    "__license__",
    "__title__",
    "__url__",
    "__version__",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "request",
    "ConnectionError",
    "ConnectTimeout",
    "FileModeWarning",
    "HTTPError",
    "JSONDecodeError",
    "ReadTimeout",
    "RequestException",
    "Timeout",
    "TooManyRedirects",
    "URLRequired",
    "PreparedRequest",
    "Request",
    "Response",
    "Session",
    "codes",
)