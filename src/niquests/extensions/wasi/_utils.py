from __future__ import annotations

import typing
from contextlib import contextmanager

from componentize_py_types import Err as _Err  # type: ignore[import-not-found]

from ...exceptions import ConnectionError, ConnectTimeout, InvalidSchema, InvalidURL, ReadTimeout, SSLError
from ...packages.urllib3._collections import HTTPHeaderDict
from ...packages.urllib3.util import parse_url
from ...utils import select_proxy

if typing.TYPE_CHECKING:
    from ...models import PreparedRequest
    from ...typing import ProxyType, TLSClientCertType, TLSVerifyType


class _WASIProxyError(ConnectionError):
    pass


def decode_field_value(value: bytes | bytearray) -> str:
    data = value if isinstance(value, bytes) else bytes(value)
    try:
        return data.decode("latin-1")
    except UnicodeDecodeError:  # Defensive:
        return data.decode("utf-8")


def validate_transport_options(
    request: PreparedRequest,
    verify: TLSVerifyType,
    cert: TLSClientCertType | None,
    proxies: ProxyType | None,
) -> tuple[str, str, str]:
    url = request.url or ""
    parsed = parse_url(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in ("ws", "wss"):
        raise InvalidSchema(
            "WebSocket is unavailable through WASI HTTP 0.2/0.3 because it does not expose upgraded duplex "
            "connections or WebSocket framing. Include the matching WASI Preview 2 or Preview 3 socket WIT "
            "interfaces in the component world to use Niquests' socket-backed WebSocket support.",
            request=request,
        )
    if scheme == "sse":
        scheme = "https"
    elif scheme == "psse":
        scheme = "http"
    if scheme not in ("http", "https"):
        raise InvalidSchema(f"WASI HTTP cannot handle URL scheme {parsed.scheme!r}", request=request)
    if not parsed.authority:
        raise InvalidURL(f"Invalid URL {url!r}: no authority", request=request)
    if select_proxy(url, proxies):
        raise _WASIProxyError(
            "WASI HTTP WIT bindings do not expose proxy support. Include the matching WASI Preview 2 or "
            "Preview 3 socket WIT interfaces to use a proxy.",
            request=request,
        )
    if verify is not True:
        raise SSLError(
            "WASI HTTPS uses the host trust policy; verify=False and custom CA bundles are unavailable.",
            request=request,
        )
    if cert is not None:
        raise SSLError("WASI HTTP does not expose TLS client certificates.", request=request)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    return scheme, parsed.authority, path


def request_headers(request: PreparedRequest, *, sse: bool = False) -> list[tuple[str, bytes]]:
    headers: list[tuple[str, bytes]] = []
    if request.headers:
        for name, value in request.headers.items():
            name_str = name if isinstance(name, str) else name.decode("latin-1")
            if name_str.lower() in ("host", "connection", "transfer-encoding"):
                continue
            value_str = value if isinstance(value, str) else decode_field_value(value)
            headers.append((name_str, value_str.encode("latin-1")))
    if sse:
        lowered = {name.lower() for name, _ in headers}
        if "accept" not in lowered:
            headers.append(("Accept", b"text/event-stream"))
        if "cache-control" not in lowered:
            headers.append(("Cache-Control", b"no-store"))
    return headers


def response_headers(entries: typing.Iterable[tuple[str, bytes]]) -> HTTPHeaderDict:
    headers = HTTPHeaderDict()
    for name, value in entries:
        headers.add(name, decode_field_value(value))
    return headers


def method_variant(types: typing.Any, method: str) -> typing.Any:
    variant = getattr(types, f"Method_{method.capitalize()}", None)
    if variant is not None and variant is not types.Method_Other:
        return variant()
    return types.Method_Other(method)


def scheme_variant(types: typing.Any, scheme: str) -> typing.Any:
    return getattr(types, "Scheme_Https" if scheme == "https" else "Scheme_Http")()


@contextmanager
def wasi_exception_mapping(url: str, *, reading: bool = False) -> typing.Iterator[None]:
    try:
        yield
    except _Err as exc:
        value = exc.value  # type: ignore[attr-defined]
        name = type(value).__name__.lower().replace("_", "").replace("-", "")
        detail = str(value) or type(value).__name__
        mapped: BaseException
        if "tlscertificate" in name or "tlsprotocol" in name or "tlsalert" in name:
            mapped = SSLError(f"WASI TLS failure for {url}: {detail}")
        elif "dnstimeout" in name or "connectiontimeout" in name:
            mapped = ConnectTimeout(f"Connection to {url} timed out")
        elif reading or "readtimeout" in name or "responsetimeout" in name:
            mapped = ReadTimeout(f"Read timed out for {url}")
        else:
            mapped = ConnectionError(f"WASI HTTP request to {url} failed: {detail}")
        raise mapped from exc


def close_resource(resource: typing.Any) -> None:
    if resource is None:
        return
    exit_method = getattr(resource, "__exit__", None)
    if exit_method is not None:
        exit_method(None, None, None)


def timeout_values(timeout: typing.Any) -> tuple[float | None, float | None]:
    if timeout is None:
        return None, None
    if isinstance(timeout, tuple):
        connect = timeout[0] if timeout else None
        read = timeout[1] if len(timeout) > 1 else connect
        if len(timeout) > 2 and read is None:
            read = timeout[2]
        return connect, read
    if hasattr(timeout, "connect_timeout"):
        connect = timeout.connect_timeout
        read = getattr(timeout, "read_timeout", None)
        total = getattr(timeout, "total", None)
        return connect or total, read or total
    value = float(timeout)
    return value, value


def set_timeouts(options: typing.Any, timeout: typing.Any) -> None:
    connect, read = timeout_values(timeout)
    if connect is not None:
        options.set_connect_timeout(int(connect * 1_000_000_000))
    if read is not None:
        for setter in (options.set_first_byte_timeout, options.set_between_bytes_timeout):
            setter(int(read * 1_000_000_000))
