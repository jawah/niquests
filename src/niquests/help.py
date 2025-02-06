"""Module containing bug report helper(s)."""

from __future__ import annotations

import json
import platform

try:
    import ssl
except ImportError:
    ssl = None  # type: ignore

import sys
import warnings
from json import JSONDecodeError

import charset_normalizer
import h11

try:
    import idna  # type: ignore[import-not-found]
except ImportError:
    idna = None  # type: ignore[assignment]

import jh2  # type: ignore
import wassima

from . import HTTPError, RequestException, Session
from . import __version__ as niquests_version
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

try:
    import wsproto  # type: ignore[import-not-found]
except ImportError:
    wsproto = None  # type: ignore


_IS_GIL_DISABLED: bool = hasattr(sys, "_is_gil_enabled") and sys._is_gil_enabled() is False


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
        implementation_version = (
            f"{sys.pypy_version_info.major}"  # type: ignore[attr-defined]
            f".{sys.pypy_version_info.minor}"  # type: ignore[attr-defined]
            f".{sys.pypy_version_info.micro}"  # type: ignore[attr-defined]
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
        "version": getattr(idna, "__version__", "N/A"),
    }

    if ssl is not None:
        system_ssl = ssl.OPENSSL_VERSION_NUMBER

        system_ssl_info = {
            "version": f"{system_ssl:x}" if system_ssl is not None else "N/A",
            "name": ssl.OPENSSL_VERSION,
        }
    else:
        system_ssl_info = {"version": "N/A", "name": "N/A"}

    return {
        "platform": platform_info,
        "implementation": implementation_info,
        "system_ssl": system_ssl_info,
        "gil": not _IS_GIL_DISABLED,
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
        "websocket": {
            "enabled": wsproto is not None,
            "wsproto": wsproto.__version__ if wsproto is not None else None,
        },
    }


pypi_session = Session()


def check_update(package_name: str, actual_version: str) -> None:
    """
    Small and concise utility to check for updates.
    """
    try:
        response = pypi_session.get(f"https://pypi.org/pypi/{package_name}/json")
        package_info = response.raise_for_status().json()

        if isinstance(package_info, dict) and "info" in package_info and "version" in package_info["info"]:
            if package_info["info"]["version"] != actual_version:
                warnings.warn(
                    f"You are using {package_name} {actual_version} and "
                    f"PyPI yield version ({package_info['info']['version']}) as the stable one. "
                    "We invite you to install this version as soon as possible. "
                    f"Run `python -m pip install {package_name} -U`.",
                    UserWarning,
                )
    except (RequestException, JSONDecodeError, HTTPError):
        pass


PACKAGE_TO_CHECK_FOR_UPGRADE = {
    "niquests": niquests_version,
    "urllib3-future": urllib3.__version__,
    "qh3": qh3.__version__ if qh3 is not None else None,
    "jh2": jh2.__version__,
    "h11": h11.__version__,
    "charset-normalizer": charset_normalizer.__version__,
    "wassima": wassima.__version__,
    "idna": idna.__version__ if idna is not None else None,
    "wsproto": wsproto.__version__ if wsproto is not None else None,
}


def main() -> None:
    """Pretty-print the bug information as JSON."""
    for package, actual_version in PACKAGE_TO_CHECK_FOR_UPGRADE.items():
        if actual_version is None:
            continue
        check_update(package, actual_version)

    if __legacy_urllib3_version__ is not None:
        warnings.warn(
            "urllib3-future is installed alongside (legacy) urllib3. This may cause compatibility issues. "
            "Some (Requests) 3rd parties may be bound to urllib3, therefor the plugins may wrongfully invoke "
            "urllib3 (legacy) instead of urllib3-future. To remediate this, run "
            "`python -m pip uninstall -y urllib3 urllib3-future`, then run `python -m pip install urllib3-future`.",
            UserWarning,
        )

    print(json.dumps(info(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
