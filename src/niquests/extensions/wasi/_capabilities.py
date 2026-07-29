from __future__ import annotations

import sys
import typing
from contextlib import suppress

from ...utils import BACKEND, _can_support_wasi_native

_IS_WASI = sys.platform == "wasi"
_HAS_NATIVE_SOCKET_SUPPORT = _IS_WASI and _can_support_wasi_native()

_WASI_P2_SOCKET: typing.Any | None = None
_WASI_P3_SOCKET: typing.Any | None = None
_WASI_P2_HTTP_TYPES: typing.Any | None = None
_WASI_P2_HTTP_HANDLER: typing.Any | None = None
_WASI_P3_HTTP_TYPES: typing.Any | None = None
_WASI_P3_HTTP_CLIENT: typing.Any | None = None


if _HAS_NATIVE_SOCKET_SUPPORT:
    with suppress(ImportError):
        from ...packages.urllib3.contrib.wasi import socket as _WASI_P2_SOCKET  # type: ignore[no-redef]

    with suppress(ImportError):
        from ...packages.urllib3.contrib.wasi._async import socket as _WASI_P3_SOCKET  # type: ignore[no-redef]


if _IS_WASI:  # pragma: no branch - generated WIT bindings only exist on WASI
    # Combined worlds receive version-qualified names.
    with suppress(ImportError):
        from wit_world.imports import wasi_http_types_0_2_0 as _WASI_P2_HTTP_TYPES  # type: ignore[import-not-found,no-redef]

    with suppress(ImportError):
        from wit_world.imports import wasi_http_types_0_3_0 as _WASI_P3_HTTP_TYPES  # type: ignore[import-not-found,no-redef]

    # A world containing only one HTTP version may receive an unqualified
    # package name, or simply `types`. Classify it by its request resource.
    _http_type_candidates = []

    with suppress(ImportError):
        from wit_world.imports import wasi_http_types as _http_types  # type: ignore[import-not-found]

        _http_type_candidates.append(_http_types)

    with suppress(ImportError):
        from wit_world.imports import types as _http_types  # type: ignore[import-not-found,no-redef]

        _http_type_candidates.append(_http_types)

    for _http_types in _http_type_candidates:
        if _WASI_P2_HTTP_TYPES is None and hasattr(_http_types, "OutgoingRequest"):
            _WASI_P2_HTTP_TYPES = _http_types
        if _WASI_P3_HTTP_TYPES is None and hasattr(_http_types, "Request"):
            _WASI_P3_HTTP_TYPES = _http_types

    with suppress(ImportError):
        from wit_world.imports import outgoing_handler as _WASI_P2_HTTP_HANDLER  # type: ignore[import-not-found,no-redef]

    if _WASI_P2_HTTP_HANDLER is None:
        with suppress(ImportError):
            from wit_world.imports import (  # type: ignore[import-not-found,no-redef]
                wasi_http_outgoing_handler_0_2_0 as _WASI_P2_HTTP_HANDLER,
            )

    with suppress(ImportError):
        from wit_world.imports import client as _WASI_P3_HTTP_CLIENT  # type: ignore[import-not-found,no-redef]

    if _WASI_P3_HTTP_CLIENT is None:
        with suppress(ImportError):
            from wit_world.imports import (  # type: ignore[import-not-found,no-redef]
                wasi_http_client_0_3_0 as _WASI_P3_HTTP_CLIENT,
            )


HAS_WASI_P2_SOCKETS = _WASI_P2_SOCKET is not None
HAS_WASI_P3_SOCKETS = _WASI_P3_SOCKET is not None
HAS_WASI_P2_HTTP = _WASI_P2_HTTP_TYPES is not None and _WASI_P2_HTTP_HANDLER is not None
HAS_WASI_P3_HTTP = _WASI_P3_HTTP_TYPES is not None and _WASI_P3_HTTP_CLIENT is not None

# Preview 1 has no generated socket bindings to probe. In a synchronous
# world with native WASI support but neither P2 sockets nor P2 HTTP,
# urllib3.future falls back to the legacy socket surface.
HAS_WASI_P1_SOCKETS = _HAS_NATIVE_SOCKET_SUPPORT and not HAS_WASI_P2_SOCKETS and not HAS_WASI_P2_HTTP

HAS_WASI_TLS_SUPPORT = _IS_WASI and BACKEND == "rtls"


__all__ = (
    "HAS_WASI_P1_SOCKETS",
    "HAS_WASI_P2_HTTP",
    "HAS_WASI_P2_SOCKETS",
    "HAS_WASI_P3_HTTP",
    "HAS_WASI_P3_SOCKETS",
    "HAS_WASI_TLS_SUPPORT",
)
