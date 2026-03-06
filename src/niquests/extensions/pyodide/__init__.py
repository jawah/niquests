"""
Pyodide Adapter for Niquests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides adapters for making HTTP requests in Pyodide (Python running
in the browser via WebAssembly). It uses the JavaScript Fetch API under the hood.

Note: Pyodide's pyfetch only supports async operations natively. The synchronous
adapter uses synchronous XMLHttpRequest which has limitations in browser environments.
"""

from __future__ import annotations

import typing

from js import Uint8Array, XMLHttpRequest  # type: ignore[import]

from ..._constant import DEFAULT_RETRIES
from ...adapters import BaseAdapter
from ...exceptions import ConnectionError
from ...models import PreparedRequest, Response
from ...packages.urllib3.exceptions import MaxRetryError
from ...packages.urllib3.response import HTTPResponse as BaseHTTPResponse
from ...packages.urllib3.util.retry import Retry
from ...structures import CaseInsensitiveDict

if typing.TYPE_CHECKING:
    from ...typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType


class _PyodideRawIO:
    """
    File-like wrapper around Pyodide XMLHttpRequest response for streaming.

    This class wraps the XHR response and provides a streaming interface
    that doesn't buffer the entire response in memory upfront when stream=True.
    """

    def __init__(
        self,
        xhr: typing.Any,
        preloaded_content: bytes | None = None,
    ) -> None:
        self._xhr = xhr
        self._preloaded_content = preloaded_content
        self._position = 0
        self._closed = False
        self._content: bytes | None = None
        self.headers: dict[str, str] = {}

    def _get_content(self) -> bytes:
        """Lazily fetch the response content from XHR."""
        if self._content is not None:
            return self._content

        if self._preloaded_content is not None:
            self._content = self._preloaded_content
            return self._content

        if self._xhr is None:
            self._content = b""
            return self._content

        # Fetch content from XHR
        try:
            if hasattr(self._xhr, "response") and self._xhr.response:
                if hasattr(self._xhr, "responseType") and self._xhr.responseType == "arraybuffer":
                    js_array = Uint8Array.new(self._xhr.response)
                    self._content = bytes(js_array.to_py())
                else:
                    self._content = self._xhr.responseText.encode("utf-8") if self._xhr.responseText else b""
            else:
                self._content = b""
        except Exception:
            self._content = self._xhr.responseText.encode("utf-8") if self._xhr.responseText else b""

        return self._content

    def read(
        self,
        amt: int | None = None,
        decode_content: bool = True,
    ) -> bytes:
        if self._closed:
            return b""

        content = self._get_content()

        if amt is None or amt < 0:
            data = content[self._position:]
            self._position = len(content)
            return data

        data = content[self._position:self._position + amt]
        self._position += len(data)
        return data

    def stream(self, amt: int, decode_content: bool = True) -> typing.Generator[bytes, None, None]:
        """Iterate over chunks of the response."""
        while True:
            chunk = self.read(amt)
            if not chunk:
                break
            yield chunk

    def close(self) -> None:
        self._closed = True
        self._xhr = None
        self._content = None

    def __iter__(self) -> typing.Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        chunk = self.read(8192)
        if not chunk:
            raise StopIteration
        return chunk


class PyodideAdapter(BaseAdapter):
    """
    Adapter for making HTTP requests in Pyodide using synchronous XMLHttpRequest.

    Note: This adapter uses synchronous XMLHttpRequest which may block the browser's
    main thread. For better performance, consider using the async adapter with
    AsyncSession instead.

    .. warning::
        Due to browser limitations, true streaming with synchronous XMLHttpRequest
        is not possible. The response body is only accessible after the request
        completes. However, when ``stream=True``, the content is read lazily
        and yielded in chunks to minimize memory pressure during iteration.

    Usage::

        >>> import niquests
        >>> s = niquests.Session()
        >>> adapter = niquests.extensions.pyodide.PyodideAdapter()
        >>> s.mount('http://', adapter)
        >>> s.mount('https://', adapter)
    """

    def __init__(self, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        """
        Initialize the Pyodide adapter.

        :param max_retries: Maximum number of retries for requests.
        """
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
        """Send a PreparedRequest using Pyodide's synchronous XMLHttpRequest."""
        retries = self.max_retries
        method = request.method or "GET"

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

                retries.sleep(base_response)
                continue

            return response

    def _do_send(
        self,
        request: PreparedRequest,
        stream: bool,
        timeout: int | float | None,
    ) -> Response:
        """Perform the actual request using synchronous XMLHttpRequest."""
        xhr = XMLHttpRequest.new()
        xhr.open(request.method or "GET", request.url, False)  # False = synchronous

        # Request arraybuffer response type to handle binary data properly
        xhr.responseType = "arraybuffer"

        # Set timeout if specified (in milliseconds)
        if timeout is not None:
            xhr.timeout = int(timeout * 1000)

        # Set request headers
        if request.headers:
            for key, value in request.headers.items():
                # Skip headers that browsers don't allow to be set
                if key.lower() not in ("host", "content-length", "connection"):
                    xhr.setRequestHeader(key, value)

        # Prepare body
        body = request.body
        if body is not None:
            if isinstance(body, str):
                body = body.encode("utf-8")
            elif isinstance(body, typing.Iterable) and not isinstance(body, (bytes, bytearray)):
                # Consume iterable body
                chunks = []
                for chunk in body:
                    if isinstance(chunk, str):
                        chunks.append(chunk.encode("utf-8"))
                    else:
                        chunks.append(chunk)
                body = b"".join(chunks)

        # Send the request
        try:
            if body:
                # Convert bytes to Uint8Array for JavaScript
                js_array = Uint8Array.new(len(body))
                for i, b in enumerate(body):
                    js_array[i] = b
                xhr.send(js_array)
            else:
                xhr.send()
        except Exception as e:
            raise ConnectionError(f"Failed to send request: {e}")

        # Parse response headers
        headers_str = xhr.getAllResponseHeaders()
        headers_dict: dict[str, str] = {}
        if headers_str:
            for line in headers_str.strip().split("\r\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers_dict[key] = value

        # Build response object
        response = Response()
        response.status_code = xhr.status
        response.headers = CaseInsensitiveDict(headers_dict)
        response.request = request
        response.url = request.url
        response.encoding = response.headers.get("content-type", "utf-8")  # type: ignore[assignment]
        response.reason = xhr.statusText or ""

        if stream:
            # For streaming: set up raw IO that reads lazily from XHR
            # Note: Due to sync XHR limitations, content is already received
            # but we defer reading/conversion until iteration
            raw_io = _PyodideRawIO(xhr)
            raw_io.headers = headers_dict
            response.raw = raw_io  # type: ignore
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        else:
            # For non-streaming: read content immediately
            response_body = b""
            if xhr.response:
                try:
                    js_array = Uint8Array.new(xhr.response)
                    response_body = bytes(js_array.to_py())
                except Exception:
                    pass

            raw_io = _PyodideRawIO(None, preloaded_content=response_body)
            raw_io.headers = headers_dict
            response.raw = raw_io  # type: ignore
            response._content = response_body

        return response

    def close(self) -> None:
        """Clean up adapter resources."""
        pass


__all__ = ("PyodideAdapter",)
