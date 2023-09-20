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

import charset_normalizer
import urllib3

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


# Check imported dependencies for compatibility.
try:
    check_compatibility(urllib3.__version__, charset_normalizer.__version__)
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or charset_normalizer ({}) doesn't match a supported "
        "version!".format(urllib3.__version__, charset_normalizer.__version__),
        RequestsDependencyWarning,
    )

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
