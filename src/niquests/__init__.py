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

import warnings

import urllib3

from .exceptions import RequestsDependencyWarning


def check_compatibility(urllib3_version: str) -> None:
    urllib3_version_split = [int(n) for n in urllib3_version.split(".")]

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version_split  # noqa: F811
    # urllib3 >= 2.0.9xx
    assert major >= 2
    assert patch >= 900


# Check imported dependencies for compatibility.
try:
    check_compatibility(urllib3.__version__)
except (AssertionError, ValueError):
    warnings.warn(
        f"""Niquests require urllib3.future installed in your environment.
        Installed urllib3 yield version {urllib3.__version__}. Make sure the patch revision is greater or equal to 900.
        You may fix this issue by executing `python -m pip uninstall urllib3 urllib3.future`,
        then `python -m pip install urllib3.future -U`.""",
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
