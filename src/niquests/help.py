"""Module containing bug report helper(s)."""
from __future__ import annotations

import json
import platform
import ssl
import sys

import charset_normalizer
import h2  # type: ignore
import h11
import idna
import urllib3
import wassima

from . import __version__ as requests_version

try:
    import qh3  # type: ignore
except ImportError:
    qh3 = None  # type: ignore

try:
    import certifi  # type: ignore
except ImportError:
    certifi = None  # type: ignore

try:
    import cryptography  # type: ignore
except ImportError:
    cryptography = None  # type: ignore

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
    urllib3_info = {"version": urllib3.__version__}

    charset_normalizer_info = {"version": charset_normalizer.__version__}

    cryptography_info = {
        "version": getattr(cryptography, "__version__", ""),
    }
    idna_info = {
        "version": getattr(idna, "__version__", ""),
    }

    system_ssl = ssl.OPENSSL_VERSION_NUMBER
    system_ssl_info = {"version": f"{system_ssl:x}" if system_ssl is not None else ""}

    return {
        "platform": platform_info,
        "implementation": implementation_info,
        "system_ssl": system_ssl_info,
        "urllib3.future": urllib3_info,
        "charset_normalizer": charset_normalizer_info,
        "cryptography": cryptography_info,
        "idna": idna_info,
        "requests": {
            "version": requests_version,
        },
        "http3": {
            "enabled": qh3 is not None,
            "qh3": qh3.__version__ if qh3 is not None else None,
        },
        "http2": {
            "h2": h2.__version__,
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
    print(json.dumps(info(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
