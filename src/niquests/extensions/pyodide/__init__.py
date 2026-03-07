from __future__ import annotations

import time
import typing
from datetime import timedelta

from pyodide.ffi import run_sync  # type: ignore[import]
from pyodide.http import pyfetch  # type: ignore[import]

from ..._constant import DEFAULT_RETRIES
from ...adapters import BaseAdapter
from ...exceptions import ConnectionError, ConnectTimeout
from ...models import PreparedRequest, Response
from ...packages.urllib3.exceptions import MaxRetryError
from ...packages.urllib3.response import BytesQueueBuffer
from ...packages.urllib3.response import HTTPResponse as BaseHTTPResponse
from ...packages.urllib3.util.retry import Retry
from ...structures import CaseInsensitiveDict
from ...utils import get_encoding_from_headers

if typing.TYPE_CHECKING:
    from ...typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType


class _PyodideRawIO:
    """File-like wrapper around a Pyodide Fetch response with true streaming via JSPI.

    When constructed with a JS Response object, reads chunks incrementally from the
    JavaScript ReadableStream using ``run_sync(reader.read())`` per chunk.
    When constructed with preloaded content (non-streaming), serves from a memory buffer.
    """

    def __init__(
        self,
        js_response: typing.Any = None,
        preloaded_content: bytes | None = None,
    ) -> None:
        self._js_response = js_response
        self._buffer = BytesQueueBuffer()
        self._closed = False
        self._finished = preloaded_content is not None or js_response is None
        self._reader: typing.Any = None
        self.headers: dict[str, str] = {}
        self.extension: typing.Any = None

        if preloaded_content is not None:
            self._buffer.put(preloaded_content)

    def _ensure_reader(self) -> None:
        """Initialize the ReadableStream reader if not already done."""
        if self._reader is None and self._js_response is not None:
            try:
                body = self._js_response.body
                if body is not None:
                    self._reader = body.getReader()
            except Exception:
                pass

    def _get_next_chunk(self) -> bytes | None:
        """Read the next chunk from the JS ReadableStream, blocking via JSPI."""
        self._ensure_reader()

        if self._reader is None:
            return None

        try:
            result = run_sync(self._reader.read())

            if result.done:
                return None

            value = result.value
            if value is not None:
                return bytes(value.to_py())
            return None
        except Exception:
            return None

    def read(
        self,
        amt: int | None = None,
        decode_content: bool = True,
    ) -> bytes:
        if self._closed:
            return self._buffer.get(len(self._buffer)) if len(self._buffer) > 0 else b""

        if self._finished:
            if len(self._buffer) == 0:
                return b""
            if amt is None or amt < 0:
                return self._buffer.get(len(self._buffer))
            return self._buffer.get(min(amt, len(self._buffer)))

        if amt is None or amt < 0:
            # Read everything remaining
            while True:
                chunk = self._get_next_chunk()
                if chunk is None:
                    break
                self._buffer.put(chunk)
            self._finished = True
            return self._buffer.get(len(self._buffer)) if len(self._buffer) > 0 else b""

        # Read until we have enough bytes or stream ends
        while len(self._buffer) < amt and not self._finished:
            chunk = self._get_next_chunk()
            if chunk is None:
                self._finished = True
                break
            self._buffer.put(chunk)

        if len(self._buffer) == 0:
            return b""

        return self._buffer.get(min(amt, len(self._buffer)))

    def stream(self, amt: int, decode_content: bool = True) -> typing.Generator[bytes, None, None]:
        """Iterate over chunks of the response."""
        while True:
            chunk = self.read(amt)
            if not chunk:
                break
            yield chunk

    def close(self) -> None:
        self._closed = True
        if self._reader is not None:
            try:
                run_sync(self._reader.cancel())
            except Exception:
                pass
        self._reader = None
        self._js_response = None

    def __iter__(self) -> typing.Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        chunk = self.read(8192)
        if not chunk:
            raise StopIteration
        return chunk


class PyodideAdapter(BaseAdapter):
    """Synchronous adapter for making HTTP requests in Pyodide using JSPI + pyfetch."""

    def __init__(self, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        super().__init__()

        if isinstance(max_retries, Retry):
            self.max_retries = max_retries
        else:
            self.max_retries = Retry.from_int(max_retries)

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], None] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], None] | None = None,
        on_early_response: typing.Callable[[Response], None] | None = None,
        multiplexed: bool = False,
    ) -> Response:
        """Send a PreparedRequest using Pyodide's pyfetch (synchronous via JSPI)."""
        retries = self.max_retries
        method = request.method or "GET"
        start = time.time()

        while True:
            try:
                response = self._do_send(request, stream, timeout)
            except Exception as err:
                try:
                    retries = retries.increment(method, request.url, error=err)
                except MaxRetryError:
                    raise

                retries.sleep()
                continue

            base_response = BaseHTTPResponse(
                body=b"",
                headers=response.headers,
                status=response.status_code,
                request_method=request.method,
                request_url=request.url,
            )

            has_retry_after = bool(response.headers.get("Retry-After"))

            if retries.is_retry(method, response.status_code, has_retry_after):
                try:
                    retries = retries.increment(method, request.url, response=base_response)
                except MaxRetryError:
                    if retries.raise_on_status:
                        raise
                    return response

                retries.sleep(base_response)
                continue

            response.elapsed = timedelta(seconds=time.time() - start)
            return response

    def _do_send(
        self,
        request: PreparedRequest,
        stream: bool,
        timeout: int | float | None,
    ) -> Response:
        """Perform the actual request using pyfetch made synchronous via JSPI."""
        url = request.url or ""
        scheme = url.split("://")[0].lower() if "://" in url else ""

        # WebSocket: delegate to browser native WebSocket API
        if scheme in ("ws", "wss"):
            return self._do_send_ws(request, url)

        # SSE: delegate to pyfetch streaming + manual SSE parsing
        if scheme in ("sse", "psse"):
            return self._do_send_sse(request, url, scheme)

        # Prepare headers
        headers_dict: dict[str, str] = {}
        if request.headers:
            for key, value in request.headers.items():
                if key.lower() not in ("host", "content-length", "connection"):
                    headers_dict[key] = value

        # Prepare body
        body = request.body
        if body is not None:
            if isinstance(body, str):
                body = body.encode("utf-8")
            elif isinstance(body, typing.Iterable) and not isinstance(body, (bytes, bytearray)):
                chunks: list[bytes] = []
                for chunk in body:
                    if isinstance(chunk, str):
                        chunks.append(chunk.encode("utf-8"))
                    elif isinstance(chunk, bytes):
                        chunks.append(chunk)
                body = b"".join(chunks)

        # Build fetch options
        fetch_options: dict[str, typing.Any] = {
            "method": request.method or "GET",
            "headers": headers_dict,
        }

        if body:
            fetch_options["body"] = body

        # Make the request — run_sync blocks via JSPI until the Promise resolves
        try:
            js_response = run_sync(pyfetch(request.url, **fetch_options))
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str:
                raise ConnectTimeout(f"Connection to {request.url} timed out")
            raise ConnectionError(f"Failed to fetch {request.url}: {e}")

        # Parse response headers
        response_headers: dict[str, str] = {}
        try:
            if hasattr(js_response, "headers"):
                js_headers = js_response.headers
                if hasattr(js_headers, "items"):
                    for key, value in js_headers.items():
                        response_headers[key] = value
                elif hasattr(js_headers, "entries"):
                    for entry in js_headers.entries():
                        response_headers[entry[0]] = entry[1]
        except Exception:
            pass

        # Build response object
        response = Response()
        response.status_code = js_response.status
        response.headers = CaseInsensitiveDict(response_headers)
        response.request = request
        response.url = js_response.url or request.url
        response.encoding = get_encoding_from_headers(response_headers)

        try:
            response.reason = js_response.status_text or ""
        except Exception:
            response.reason = ""

        if stream:
            # Streaming: pass the underlying JS Response to the raw IO
            # so it can read chunks incrementally via run_sync(reader.read())
            raw_io = _PyodideRawIO(js_response=js_response.js_response)
            raw_io.headers = response_headers
            response.raw = raw_io  # type: ignore
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        else:
            # Non-streaming: read full body upfront
            try:
                response_body: bytes = run_sync(js_response.bytes())
            except Exception:
                response_body = b""

            raw_io = _PyodideRawIO(preloaded_content=response_body)
            raw_io.headers = response_headers
            response.raw = raw_io  # type: ignore
            response._content = response_body

        return response

    def _do_send_ws(self, request: PreparedRequest, url: str) -> Response:
        """Handle WebSocket connections via browser native WebSocket API."""
        from ._ws import PyodideWebSocketExtension

        try:
            ext = PyodideWebSocketExtension(url)
        except Exception as e:
            raise ConnectionError(f"WebSocket connection to {url} failed: {e}")

        response = Response()
        response.status_code = 101
        response.headers = CaseInsensitiveDict({"upgrade": "websocket", "connection": "upgrade"})
        response.request = request
        response.url = url
        response.reason = "Switching Protocols"

        raw_io = _PyodideRawIO()
        raw_io.extension = ext
        response.raw = raw_io  # type: ignore
        response._content = b""

        return response

    def _do_send_sse(self, request: PreparedRequest, url: str, scheme: str) -> Response:
        """Handle SSE connections via pyfetch streaming + manual parsing."""
        from ._sse import PyodideSSEExtension

        http_url = url.replace("sse://", "https://", 1) if scheme == "sse" else url.replace("psse://", "http://", 1)

        # Pass through user-provided headers
        headers_dict: dict[str, str] = {}
        if request.headers:
            for key, value in request.headers.items():
                if key.lower() not in ("host", "content-length", "connection"):
                    headers_dict[key] = value

        try:
            ext = PyodideSSEExtension(http_url, headers=headers_dict)
        except Exception as e:
            raise ConnectionError(f"SSE connection to {url} failed: {e}")

        response = Response()
        response.status_code = 200
        response.headers = CaseInsensitiveDict({"content-type": "text/event-stream"})
        response.request = request
        response.url = url
        response.reason = "OK"

        raw_io = _PyodideRawIO()
        raw_io.extension = ext
        response.raw = raw_io  # type: ignore
        response._content = False  # type: ignore[assignment]
        response._content_consumed = False

        return response

    def close(self) -> None:
        """Clean up adapter resources."""
        pass


__all__ = ("PyodideAdapter",)
