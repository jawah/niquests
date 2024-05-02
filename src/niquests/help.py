"""Module containing bug report helper(s)."""

from __future__ import annotations

import json
import platform
import ssl
import sys
import warnings
from json import JSONDecodeError

import charset_normalizer
import jh2  # type: ignore
import h11
import idna
import wassima

from . import RequestException
from . import __version__ as niquests_version
from . import get
from ._compat import HAS_LEGACY_URLLIB3

if HAS_LEGACY_URLLIB3 is True:
    import urllib3_future as urllib3

    try:
        from urllib3 import __version__ as __legacy_urllib3_version__
    except (ImportError, AttributeError):
        __legacy_urllib3_version__ = None  # type: ignore[assignment]
else:
    import urllib3  # type: ignore[no-redef]

    __legacy_urllib3_version__ = None  # type: ignore[assignment]

try:
    import qh3  # type: ignore
except ImportError:
    qh3 = None  # type: ignore

try:
    import certifi  # type: ignore
except ImportError:
    certifi = None  # type: ignore

try:
    from .extensions._ocsp import verify as ocsp_verify
except ImportError:
    ocsp_verify = None  # type: ignore


def _implementation():
    """Return a dict with the Python implementation and version.

    Provide both the name and the version of the Python implementation
    currently running. For example, on CPython 3.10.3 it will return
    {'name': 'CPython', 'version': '3.10.3'}.

    This function works best on CPython and PyPy: in particular, it probably
    doesn't work for Jython or IronPython. Future investigation should be done
    to work out the correct shape of the code for those platforms.
    """
    implementation = platform.python_implementation()

    if implementation == "CPython":
        implementation_version = platform.python_version()
    elif implementation == "PyPy":
        implementation_version = "{}.{}.{}".format(
            sys.pypy_version_info.major,  # type: ignore[attr-defined]
            sys.pypy_version_info.minor,  # type: ignore[attr-defined]
            sys.pypy_version_info.micro,  # type: ignore[attr-defined]
        )
        if sys.pypy_version_info.releaselevel != "final":  # type: ignore[attr-defined]
            implementation_version = "".join(
                [implementation_version, sys.pypy_version_info.releaselevel]  # type: ignore[attr-defined]
            )
    elif implementation == "Jython":
        implementation_version = platform.python_version()  # Complete Guess
    elif implementation == "IronPython":
        implementation_version = platform.python_version()  # Complete Guess
    else:
        implementation_version = "Unknown"

    return {"name": implementation, "version": implementation_version}


def info():
    """Generate information for a bug report."""
    try:
        platform_info = {
            "system": platform.system(),
            "release": platform.release(),
        }
    except OSError:
        platform_info = {
            "system": "Unknown",
            "release": "Unknown",
        }

    implementation_info = _implementation()
    urllib3_info = {
        "version": urllib3.__version__,
        "cohabitation_version": __legacy_urllib3_version__,
    }

    charset_normalizer_info = {"version": charset_normalizer.__version__}

    idna_info = {
        "version": getattr(idna, "__version__", ""),
    }

    system_ssl = ssl.OPENSSL_VERSION_NUMBER
    system_ssl_info = {
        "version": f"{system_ssl:x}" if system_ssl is not None else "N/A"
    }

    return {
        "platform": platform_info,
        "implementation": implementation_info,
        "system_ssl": system_ssl_info,
        "urllib3.future": urllib3_info,
        "charset_normalizer": charset_normalizer_info,
        "idna": idna_info,
        "niquests": {
            "version": niquests_version,
        },
        "http3": {
            "enabled": qh3 is not None,
            "qh3": qh3.__version__ if qh3 is not None else None,
        },
        "http2": {
            "jh2": jh2.__version__,
        },
        "http1": {
            "h11": h11.__version__,
        },
        "wassima": {
            "enabled": wassima.RUSTLS_LOADED,
            "certifi_fallback": wassima.RUSTLS_LOADED is False and certifi is not None,
            "version": wassima.__version__,
        },
        "ocsp": {"enabled": ocsp_verify is not None},
    }


def main() -> None:
    """Pretty-print the bug information as JSON."""
    try:
        response = get("https://pypi.org/pypi/niquests/json")
        package_info = response.json()

        if (
            isinstance(package_info, dict)
            and "info" in package_info
            and "version" in package_info["info"]
        ):
            if package_info["info"]["version"] != niquests_version:
                warnings.warn(
                    f"You are using Niquests {niquests_version} and PyPI yield version ({package_info['info']['version']}) as the stable one. "
                    "We invite you to install this version as soon as possible. Run `python -m pip install niquests -U`.",
                    UserWarning,
                )
    except (RequestException, JSONDecodeError):
        pass

    print(json.dumps(info(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
