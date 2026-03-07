from __future__ import annotations

import asyncio
import time
import typing
from datetime import timedelta

from pyodide.http import pyfetch  # type: ignore[import]

from ...._constant import DEFAULT_RETRIES
from ....adapters import AsyncBaseAdapter
from ....exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from ....models import AsyncResponse, PreparedRequest, Response
from ....packages.urllib3._async.response import AsyncHTTPResponse as BaseHTTPResponse
from ....packages.urllib3.contrib.ssa._timeout import timeout as asyncio_timeout
from ....packages.urllib3.exceptions import MaxRetryError
from ....packages.urllib3.response import BytesQueueBuffer
from ....packages.urllib3.util.retry import Retry
from ....structures import CaseInsensitiveDict
from ....utils import _swap_context, get_encoding_from_headers

if typing.TYPE_CHECKING:
    from ....typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType


class _AsyncPyodideRawIO:
    """
    Async file-like wrapper around Pyodide Fetch response for true streaming.

    This class uses the JavaScript ReadableStream API through Pyodide to provide
    genuine streaming support without buffering the entire response in memory.
    """

    def __init__(
        self,
        js_response: typing.Any,  # JavaScript Response object
        timeout: float | None = None,
    ) -> None:
        self._js_response = js_response
        self._timeout = timeout
        self._buffer = BytesQueueBuffer()
        self._closed = False
        self._finished = False
        self._reader: typing.Any = None  # JavaScript ReadableStreamDefaultReader
        self.headers: dict[str, str] = {}
        self.extension: typing.Any = None

    async def _ensure_reader(self) -> None:
        """Initialize the stream reader if not already done."""
        if self._reader is None and self._js_response is not None:
            try:
                body = self._js_response.body
                if body is not None:
                    self._reader = body.getReader()
            except Exception:
                pass

    async def read(self, amt: int | None = None, decode_content: bool = True) -> bytes:
        """
        Read up to `amt` bytes from the response stream.

        When `amt` is None, reads the entire remaining response.
        """
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
            async for chunk in self._stream_chunks():
                self._buffer.put(chunk)
            self._finished = True
            return self._buffer.get(len(self._buffer)) if len(self._buffer) > 0 else b""

        # Read until we have enough bytes or stream ends
        while len(self._buffer) < amt and not self._finished:
            chunk = await self._get_next_chunk()  # type: ignore[assignment]
            if chunk is None:
                self._finished = True
                break
            self._buffer.put(chunk)

        if len(self._buffer) == 0:
            return b""

        return self._buffer.get(min(amt, len(self._buffer)))

    async def _get_next_chunk(self) -> bytes | None:
        """Read the next chunk from the JavaScript ReadableStream."""
        await self._ensure_reader()

        if self._reader is None:
            return None

        try:
            if self._timeout is not None:
                async with asyncio_timeout(self._timeout):
                    result = await self._reader.read()
            else:
                result = await self._reader.read()

            if result.done:
                return None

            value = result.value
            if value is not None:
                # Convert Uint8Array to bytes
                return bytes(value.to_py())
            return None
        except asyncio.TimeoutError:
            raise ReadTimeout("Read timed out while streaming Pyodide response")
        except Exception:
            return None

    async def _stream_chunks(self) -> typing.AsyncGenerator[bytes, None]:
        """Async generator that yields chunks from the stream."""
        await self._ensure_reader()

        if self._reader is None:
            return

        while True:
            chunk = await self._get_next_chunk()
            if chunk is None:
                break
            yield chunk

    def stream(self, amt: int, decode_content: bool = True) -> typing.AsyncGenerator[bytes, None]:
        """Return an async generator that yields chunks of `amt` bytes."""
        return self._async_stream(amt)

    async def _async_stream(self, amt: int) -> typing.AsyncGenerator[bytes, None]:
        """Internal async generator for streaming."""
        while True:
            chunk = await self.read(amt)
            if not chunk:
                break
            yield chunk

    async def close(self) -> None:
        """Close the stream and release resources."""
        self._closed = True
        if self._reader is not None:
            try:
                await self._reader.cancel()
            except Exception:
                pass
        self._reader = None
        self._js_response = None

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        return self

    async def __anext__(self) -> bytes:
        chunk = await self.read(8192)
        if not chunk:
            raise StopAsyncIteration
        return chunk


class AsyncPyodideAdapter(AsyncBaseAdapter):
    """Async adapter for making HTTP requests in Pyodide using the native pyfetch API."""

    def __init__(self, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        """
        Initialize the async Pyodide adapter.

        :param max_retries: Maximum number of retries for requests.
        """
        super().__init__()

        if isinstance(max_retries, Retry):
            self.max_retries = max_retries
        else:
            self.max_retries = Retry.from_int(max_retries)

    async def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], typing.Awaitable[None]] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None = None,
        on_early_response: typing.Callable[[Response], typing.Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> AsyncResponse:
        """Send a PreparedRequest using Pyodide's pyfetch (JavaScript Fetch API)."""
        retries = self.max_retries
        method = request.method or "GET"
        start = time.time()

        while True:
            try:
                response = await self._do_send(request, stream, timeout)
            except Exception as err:
                try:
                    retries = retries.increment(method, request.url, error=err)
                except MaxRetryError:
                    raise

                await retries.async_sleep()
                continue

            # We rely on the urllib3 implementation for retries
            # so we basically mock a response to get it to work
            base_response = BaseHTTPResponse(
                body=b"",
                headers=response.headers,
                status=response.status_code,
                request_method=request.method,
                request_url=request.url,
            )

            # Check if we should retry based on status code
            has_retry_after = bool(response.headers.get("Retry-After"))

            if retries.is_retry(method, response.status_code, has_retry_after):
                try:
                    retries = retries.increment(method, request.url, response=base_response)
                except MaxRetryError:
                    if retries.raise_on_status:
                        raise
                    return response

                await retries.async_sleep(base_response)
                continue

            response.elapsed = timedelta(seconds=time.time() - start)
            return response

    async def _do_send(
        self,
        request: PreparedRequest,
        stream: bool,
        timeout: int | float | None,
    ) -> AsyncResponse:
        """Perform the actual request using Pyodide's pyfetch."""
        url = request.url or ""
        scheme = url.split("://")[0].lower() if "://" in url else ""

        # WebSocket: delegate to browser native WebSocket API
        if scheme in ("ws", "wss"):
            return await self._do_send_ws(request, url)

        # SSE: delegate to pyfetch streaming + manual SSE parsing
        if scheme in ("sse", "psse"):
            return await self._do_send_sse(request, url, scheme)

        # Prepare headers
        headers_dict: dict[str, str] = {}
        if request.headers:
            for key, value in request.headers.items():
                # Skip headers that browsers don't allow to be set
                if key.lower() not in ("host", "content-length", "connection"):
                    headers_dict[key] = value

        # Prepare body
        body = request.body
        if body is not None:
            if isinstance(body, str):
                body = body.encode("utf-8")
            elif hasattr(body, "__aiter__"):
                # Consume async iterable body
                chunks: list[bytes] = []
                async for chunk in body:  # type: ignore[union-attr]
                    if isinstance(chunk, str):
                        chunks.append(chunk.encode("utf-8"))
                    else:
                        chunks.append(chunk)
                body = b"".join(chunks)
            elif isinstance(body, typing.Iterable) and not isinstance(body, (bytes, bytearray)):
                # Consume sync iterable body
                chunks = []
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

        # Make the request with timeout
        try:
            if timeout is not None:
                async with asyncio_timeout(timeout):
                    js_response = await pyfetch(request.url, **fetch_options)
            else:
                js_response = await pyfetch(request.url, **fetch_options)
        except asyncio.TimeoutError:
            raise ConnectTimeout(f"Connection to {request.url} timed out")
        except Exception as e:
            raise ConnectionError(f"Failed to fetch {request.url}: {e}")

        # Parse response headers
        response_headers: dict[str, str] = {}
        try:
            # Pyodide's FetchResponse has headers as a dict-like object
            if hasattr(js_response, "headers"):
                js_headers = js_response.headers
                if hasattr(js_headers, "items"):
                    for key, value in js_headers.items():
                        response_headers[key] = value
                elif hasattr(js_headers, "entries"):
                    # JavaScript Headers.entries() returns an iterator
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

        # Try to get status text
        try:
            response.reason = js_response.status_text or ""
        except Exception:
            response.reason = ""

        if stream:
            # For streaming: set up async raw IO using the JS Response object
            # This provides true streaming without buffering entire response
            raw_io = _AsyncPyodideRawIO(js_response.js_response, timeout)
            raw_io.headers = response_headers
            response.raw = raw_io  # type: ignore
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        else:
            # For non-streaming: get full response body
            try:
                if timeout is not None:
                    async with asyncio_timeout(timeout):
                        response_body = await js_response.bytes()
                else:
                    response_body = await js_response.bytes()
            except asyncio.TimeoutError:
                raise ReadTimeout(f"Read timed out for {request.url}")

            response._content = response_body
            raw_io = _AsyncPyodideRawIO(None, timeout)
            raw_io.headers = response_headers
            response.raw = raw_io  # type: ignore

        _swap_context(response)

        return response  # type: ignore[return-value]

    async def _do_send_ws(self, request: PreparedRequest, url: str) -> AsyncResponse:
        """Handle WebSocket connections via browser native WebSocket API."""
        from ._ws import AsyncPyodideWebSocketExtension

        ext = AsyncPyodideWebSocketExtension()

        try:
            await ext.start(url)
        except Exception as e:
            raise ConnectionError(f"WebSocket connection to {url} failed: {e}")

        response = Response()
        response.status_code = 101
        response.headers = CaseInsensitiveDict({"upgrade": "websocket", "connection": "upgrade"})
        response.request = request
        response.url = url
        response.reason = "Switching Protocols"

        raw_io = _AsyncPyodideRawIO(None)
        raw_io.extension = ext
        response.raw = raw_io  # type: ignore
        response._content = b""

        _swap_context(response)

        return response  # type: ignore[return-value]

    async def _do_send_sse(self, request: PreparedRequest, url: str, scheme: str) -> AsyncResponse:
        """Handle SSE connections via pyfetch streaming + manual parsing."""
        from ._sse import AsyncPyodideSSEExtension

        http_url = url.replace("sse://", "https://", 1) if scheme == "sse" else url.replace("psse://", "http://", 1)

        # Pass through user-provided headers
        headers_dict: dict[str, str] = {}
        if request.headers:
            for key, value in request.headers.items():
                if key.lower() not in ("host", "content-length", "connection"):
                    headers_dict[key] = value

        ext = AsyncPyodideSSEExtension()

        try:
            await ext.start(http_url, headers=headers_dict)
        except Exception as e:
            raise ConnectionError(f"SSE connection to {url} failed: {e}")

        response = Response()
        response.status_code = 200
        response.headers = CaseInsensitiveDict({"content-type": "text/event-stream"})
        response.request = request
        response.url = url
        response.reason = "OK"

        raw_io = _AsyncPyodideRawIO(None)
        raw_io.extension = ext
        response.raw = raw_io  # type: ignore
        response._content = False  # type: ignore[assignment]
        response._content_consumed = False

        _swap_context(response)

        return response  # type: ignore[return-value]

    async def close(self) -> None:
        """Clean up adapter resources."""
        pass


__all__ = ("AsyncPyodideAdapter",)
