"""Module containing bug report helper(s)."""
from __future__ import annotations

import json
import platform
import ssl
import sys

import charset_normalizer
import idna
import urllib3

from . import __version__ as requests_version

try:
    from urllib3.contrib import pyopenssl
except (ImportError, AttributeError):
    pyopenssl = None  # type: ignore
    OpenSSL = None  # type: ignore
    cryptography = None  # type: ignore
else:
    import cryptography  # type: ignore
    import OpenSSL  # type: ignore


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

    pyopenssl_info = {
        "version": None,
        "openssl_version": "",
    }
    if OpenSSL:
        pyopenssl_info = {
            "version": OpenSSL.__version__,
            "openssl_version": f"{OpenSSL.SSL.OPENSSL_VERSION_NUMBER:x}",
        }
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
        "using_pyopenssl": pyopenssl is not None,
        "pyOpenSSL": pyopenssl_info,
        "urllib3": urllib3_info,
        "charset_normalizer": charset_normalizer_info,
        "cryptography": cryptography_info,
        "idna": idna_info,
        "requests": {
            "version": requests_version,
        },
    }


def main() -> None:
    """Pretty-print the bug information as JSON."""
    print(json.dumps(info(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
