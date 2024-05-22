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

from __future__ import annotations

# Set default logging handler to avoid "No handler found" warnings.
import logging
import warnings
from logging import NullHandler

from ._compat import HAS_LEGACY_URLLIB3

if HAS_LEGACY_URLLIB3 is False:
    from urllib3.exceptions import DependencyWarning
else:
    from urllib3_future.exceptions import DependencyWarning  # type: ignore[assignment]

# urllib3's DependencyWarnings should be silenced.
warnings.simplefilter("ignore", DependencyWarning)

# ruff: noqa: E402
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
from ._async import AsyncSession
from .api import delete, get, head, options, patch, post, put, request
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    RequestsDependencyWarning,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response, AsyncResponse
from .sessions import Session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

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
    "AsyncSession",
    "AsyncResponse",
)
