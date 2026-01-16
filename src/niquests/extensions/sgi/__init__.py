from __future__ import annotations

import typing

from ..._constant import DEFAULT_RETRIES
from ...adapters import BaseAdapter
from ...models import PreparedRequest, Response
from ...packages.urllib3.exceptions import MaxRetryError
from ...packages.urllib3.response import BytesQueueBuffer
from ...packages.urllib3.response import HTTPResponse as BaseHTTPResponse
from ...packages.urllib3.util.retry import Retry
from ...structures import CaseInsensitiveDict

if typing.TYPE_CHECKING:
    from ...typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType, WSGIApp

from io import BytesIO


class _WSGIRawIO:
    """File-like wrapper around a WSGI response iterator for streaming."""

    def __init__(self, generator: typing.Generator[bytes, None, None], headers: list[tuple[str, str]]) -> None:
        self._generator = generator
        self._buffer = BytesQueueBuffer()
        self._closed = False
        self.headers = headers

    def read(
        self,
        amt: int | None = None,
        decode_content: bool = True,
    ) -> bytes:
        if self._closed:
            return b""

        if amt is None or amt < 0:
            # Read all remaining
            for chunk in self._generator:
                self._buffer.put(chunk)
            return self._buffer.get(len(self._buffer))

        # Read specific amount
        while len(self._buffer) < amt:
            try:
                self._buffer.put(next(self._generator))
            except StopIteration:
                break

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
        if hasattr(self._generator, "close"):
            self._generator.close()

    def __iter__(self) -> typing.Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        chunk = self.read(8192)
        if not chunk:
            raise StopIteration
        return chunk


class WebServerGatewayInterface(BaseAdapter):
    """Adapter for making requests to WSGI applications directly."""

    def __init__(self, app: WSGIApp, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        """
        Initialize the WSGI adapter.

        :param app: A WSGI application callable.
        :param max_retries: Maximum number of retries for requests.
        """
        super().__init__()
        self.app = app

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
        """Send a PreparedRequest to the WSGI application."""
        retries = self.max_retries
        method = request.method or "GET"

        while True:
            try:
                response = self._do_send(request, stream)
            except Exception as err:
                try:
                    retries = retries.increment(method, request.url, error=err)
                except MaxRetryError:
                    raise

                retries.sleep()
                continue

            # we rely on the urllib3 implementation for retries
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

    def _do_send(self, request: PreparedRequest, stream: bool) -> Response:
        """Perform the actual WSGI request."""
        environ = self._create_environ(request)

        status_code = None
        response_headers: list[tuple[str, str]] = []

        def start_response(status: str, headers: list[tuple[str, str]], exc_info=None):
            nonlocal status_code, response_headers
            status_code = int(status.split(" ", 1)[0])
            response_headers = headers

        result = self.app(environ, start_response)

        response = Response()

        response.status_code = status_code
        response.headers = CaseInsensitiveDict(response_headers)
        response.request = request
        response.url = request.url
        response.encoding = response.headers.get("content-type", "utf-8")  # type: ignore[assignment]

        # Wrap the WSGI iterator for streaming
        def generate():
            try:
                yield from result
            finally:
                if hasattr(result, "close"):
                    result.close()

        response.raw = _WSGIRawIO(generate(), response_headers)  # type: ignore

        if stream:
            response._content = False  # Indicate content not yet consumed
            response._content_consumed = False
        else:
            # Consume all content immediately
            body_chunks: list[bytes] = []
            try:
                for chunk in result:
                    body_chunks.append(chunk)
            finally:
                if hasattr(result, "close"):
                    result.close()
            response._content = b"".join(body_chunks)

        return response

    def _create_environ(self, request: PreparedRequest) -> dict:
        """Create a WSGI environ dict from a PreparedRequest."""
        from urllib.parse import unquote, urlparse

        parsed = urlparse(request.url)

        body = request.body or b""

        if isinstance(body, str):
            body = body.encode("utf-8")
        elif isinstance(body, typing.Iterable) and not isinstance(body, (str, bytes, bytearray, tuple)):
            tmp = b""

            for chunk in body:
                tmp += chunk  # type: ignore[operator]

            body = tmp

        environ = {
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": "",
            "PATH_INFO": unquote(parsed.path) or "/",
            "QUERY_STRING": parsed.query or "",
            "SERVER_NAME": parsed.hostname or "localhost",
            "SERVER_PORT": str(parsed.port or (443 if parsed.scheme == "https" else 80)),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": parsed.scheme or "http",
            "wsgi.input": BytesIO(body),  # type: ignore[arg-type]
            "wsgi.errors": BytesIO(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": str(len(body)),  # type: ignore[arg-type]
        }

        if request.headers:
            for key, value in request.headers.items():
                key_upper = key.upper().replace("-", "_")
                if key_upper == "CONTENT_TYPE":
                    environ["CONTENT_TYPE"] = value
                elif key_upper == "CONTENT_LENGTH":
                    environ["CONTENT_LENGTH"] = value
                else:
                    environ[f"HTTP_{key_upper}"] = value

        return environ

    def close(self) -> None:
        """Clean up adapter resources."""
        pass
