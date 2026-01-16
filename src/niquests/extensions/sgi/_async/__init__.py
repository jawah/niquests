from __future__ import annotations

import asyncio
import contextlib
import threading
import typing
from concurrent.futures import Future

from ...._constant import DEFAULT_RETRIES
from ....adapters import AsyncBaseAdapter, BaseAdapter
from ....exceptions import ConnectTimeout, ReadTimeout
from ....models import AsyncResponse, PreparedRequest, Response
from ....packages.urllib3._async.response import AsyncHTTPResponse as BaseHTTPResponse
from ....packages.urllib3.contrib.ssa._timeout import timeout as asyncio_timeout
from ....packages.urllib3.exceptions import MaxRetryError
from ....packages.urllib3.response import BytesQueueBuffer
from ....packages.urllib3.util.retry import Retry
from ....structures import CaseInsensitiveDict
from ....utils import _swap_context

if typing.TYPE_CHECKING:
    from ....typing import ASGIApp, ASGIMessage, ProxyType, RetryType, TLSClientCertType, TLSVerifyType


class _ASGIRawIO:
    """Async file-like wrapper around an ASGI response for true async streaming."""

    def __init__(
        self,
        response_queue: asyncio.Queue[ASGIMessage | None],
        response_complete: asyncio.Event,
        timeout: float | None = None,
    ) -> None:
        self._response_queue = response_queue
        self._response_complete = response_complete
        self._timeout = timeout
        self._buffer = BytesQueueBuffer()
        self._closed = False
        self._finished = False
        self._task: asyncio.Task | None = None
        self.headers: dict | None = None

    async def read(self, amt: int | None = None, decode_content: bool = True) -> bytes:
        if self._closed or self._finished:
            return self._buffer.get(len(self._buffer))

        if amt is None or amt < 0:
            async for chunk in self._async_iter_chunks():
                self._buffer.put(chunk)
            self._finished = True
            return self._buffer.get(len(self._buffer))

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
        try:
            async with asyncio_timeout(self._timeout):
                message = await self._response_queue.get()
            if message is None:
                return None
            if message["type"] == "http.response.body":
                return message.get("body", b"")
            return None
        except asyncio.TimeoutError:
            await self._cancel_task()
            raise ReadTimeout("Read timed out while streaming ASGI response")
        except asyncio.CancelledError:
            return None

    async def _async_iter_chunks(self) -> typing.AsyncGenerator[bytes]:
        while True:
            try:
                async with asyncio_timeout(self._timeout):
                    message = await self._response_queue.get()
            except asyncio.TimeoutError:
                await self._cancel_task()
                raise ReadTimeout("Read timed out while streaming ASGI response")
            if message is None:
                break
            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    yield chunk

    async def _cancel_task(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def stream(self, amt: int, decode_content: bool = True) -> typing.AsyncGenerator[bytes]:
        return self._async_stream(amt)

    async def _async_stream(self, amt: int) -> typing.AsyncGenerator[bytes]:
        while True:
            chunk = await self.read(amt)
            if not chunk:
                break
            yield chunk

    def close(self) -> None:
        self._closed = True
        self._response_complete.set()

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        return self._async_iter_self()

    async def _async_iter_self(self) -> typing.AsyncIterator[bytes]:
        async for chunk in self._async_iter_chunks():
            yield chunk

    async def __anext__(self) -> bytes:
        chunk = await self.read(8192)
        if not chunk:
            raise StopAsyncIteration
        return chunk


class AsyncServerGatewayInterface(AsyncBaseAdapter):
    """Adapter for making requests to ASGI applications directly."""

    def __init__(
        self,
        app: ASGIApp,
        raise_app_exceptions: bool = True,
        max_retries: RetryType = DEFAULT_RETRIES,
        lifespan_state: dict[str, typing.Any] | None = None,
    ) -> None:
        super().__init__()
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self._lifespan_state = lifespan_state

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
        """Send a PreparedRequest to the ASGI application."""
        retries = self.max_retries
        method = request.method or "GET"

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

                await retries.async_sleep(base_response)
                continue

            return response

    async def _do_send(
        self,
        request: PreparedRequest,
        stream: bool,
        timeout: int | float | None,
    ) -> AsyncResponse:
        """Perform the actual ASGI request."""
        scope = self._create_scope(request)

        body = request.body or b""
        body_iter: typing.AsyncIterator[bytes] | typing.AsyncIterator[str] | None = None

        # Check if body is an async iterable
        if hasattr(body, "__aiter__"):
            body_iter = body.__aiter__()
            body = b""  # Will be streamed
        elif isinstance(body, str):
            body = body.encode("utf-8")

        request_complete = False
        response_complete = asyncio.Event()
        response_queue: asyncio.Queue[ASGIMessage | None] = asyncio.Queue()
        app_exception: Exception | None = None

        async def receive() -> ASGIMessage:
            nonlocal request_complete
            if request_complete:
                await response_complete.wait()
                return {"type": "http.disconnect"}

            if body_iter is not None:
                # Stream chunks from async iterable
                try:
                    chunk = await body_iter.__anext__()
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    return {"type": "http.request", "body": chunk, "more_body": True}
                except StopAsyncIteration:
                    request_complete = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            else:
                # Single body chunk
                request_complete = True
                return {"type": "http.request", "body": body, "more_body": False}

        async def send_func(message: ASGIMessage) -> None:
            await response_queue.put(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_complete.set()

        async def run_app() -> None:
            nonlocal app_exception
            try:
                await self.app(scope, receive, send_func)
            except Exception as ex:
                app_exception = ex
            finally:
                await response_queue.put(None)

        if stream:
            return await self._stream_response(
                request, response_queue, response_complete, run_app, lambda: app_exception, timeout
            )
        else:
            return await self._buffered_response(
                request, response_queue, response_complete, run_app, lambda: app_exception, timeout
            )

    async def _stream_response(
        self,
        request: PreparedRequest,
        response_queue: asyncio.Queue[ASGIMessage | None],
        response_complete: asyncio.Event,
        run_app: typing.Callable[[], typing.Awaitable[None]],
        get_exception: typing.Callable[[], Exception | None],
        timeout: float | None,
    ) -> AsyncResponse:
        status_code: int | None = None
        response_headers: list[tuple[bytes, bytes]] = []

        task = asyncio.create_task(run_app())  # type: ignore[var-annotated,arg-type]

        try:
            # Wait for http.response.start with timeout
            async with asyncio_timeout(timeout):
                while True:
                    message = await response_queue.get()
                    if message is None:
                        break
                    if message["type"] == "http.response.start":
                        status_code = message["status"]
                        response_headers = message.get("headers", [])
                        break

            headers_dict = {k.decode("latin-1"): v.decode("latin-1") for k, v in response_headers}

            raw_io = _ASGIRawIO(response_queue, response_complete, timeout)
            raw_io.headers = headers_dict
            raw_io._task = task

            response = Response()
            response.status_code = status_code
            response.headers = CaseInsensitiveDict(headers_dict)
            response.request = request
            response.url = request.url
            response.encoding = response.headers.get("content-type", "utf-8")  # type: ignore[assignment]
            response.raw = raw_io  # type: ignore
            response._content = False
            response._content_consumed = False
            _swap_context(response)

            return response  # type: ignore

        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise ConnectTimeout("Timed out waiting for ASGI response headers")

        except Exception:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise

    async def _buffered_response(
        self,
        request: PreparedRequest,
        response_queue: asyncio.Queue[ASGIMessage | None],
        response_complete: asyncio.Event,
        run_app: typing.Callable[[], typing.Awaitable[None]],
        get_exception: typing.Callable[[], Exception | None],
        timeout: float | None,
    ) -> AsyncResponse:
        status_code: int | None = None
        response_headers: list[tuple[bytes, bytes]] = []
        body_chunks: list[bytes] = []

        task = asyncio.create_task(run_app())  # type: ignore[var-annotated,arg-type]

        try:
            async with asyncio_timeout(timeout):
                while True:
                    message = await response_queue.get()
                    if message is None:
                        break
                    if message["type"] == "http.response.start":
                        status_code = message["status"]
                        response_headers = message.get("headers", [])
                    elif message["type"] == "http.response.body":
                        chunk = message.get("body", b"")
                        if chunk:
                            body_chunks.append(chunk)

                await task

        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise ReadTimeout("Timed out reading ASGI response body")

        except Exception:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise

        if self.raise_app_exceptions and get_exception() is not None:
            raise get_exception()  # type: ignore

        headers_dict = {k.decode("latin-1"): v.decode("latin-1") for k, v in response_headers}

        response = Response()
        response.status_code = status_code
        response.headers = CaseInsensitiveDict(headers_dict)
        response.request = request
        response.url = request.url
        response.encoding = response.headers.get("content-type", "utf-8")  # type: ignore[assignment]
        response._content = b"".join(body_chunks)
        response.raw = _ASGIRawIO(response_queue, response_complete, timeout)  # type: ignore
        response.raw.headers = headers_dict

        _swap_context(response)

        return response  # type: ignore[return-value]

    def _create_scope(self, request: PreparedRequest) -> dict:
        from urllib.parse import unquote, urlparse

        parsed = urlparse(request.url)
        headers: list[tuple[bytes, bytes]] = []
        if request.headers:
            for key, value in request.headers.items():
                headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

        scope: dict[str, typing.Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "scheme": "http",
            "path": unquote(parsed.path) or "/",
            "query_string": (parsed.query or "").encode("latin-1"),  # type: ignore[union-attr]
            "root_path": "",
            "headers": headers,
            "server": (
                parsed.hostname or "localhost",
                parsed.port or (443 if parsed.scheme == "https" else 80),
            ),
        }

        # Include lifespan state if available (for frameworks like Starlette that use it)
        if self._lifespan_state is not None:
            scope["state"] = self._lifespan_state.copy()

        return scope

    async def close(self) -> None:
        pass


class ThreadAsyncServerGatewayInterface(BaseAdapter):
    """Synchronous adapter for ASGI applications using a background event loop."""

    def __init__(
        self,
        app: ASGIApp,
        raise_app_exceptions: bool = True,
        max_retries: RetryType = DEFAULT_RETRIES,
    ) -> None:
        super().__init__()
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions

        if isinstance(max_retries, Retry):
            self.max_retries = max_retries
        else:
            self.max_retries = Retry.from_int(max_retries)

        self._async_adapter: AsyncServerGatewayInterface | None = None
        self._loop: typing.Any = None  # asyncio.AbstractEventLoop
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._lifespan_task: asyncio.Task | None = None
        self._lifespan_receive_queue: asyncio.Queue[ASGIMessage] | None = None
        self._lifespan_startup_complete = threading.Event()
        self._lifespan_startup_failed: Exception | None = None
        self._lifespan_state: dict[str, typing.Any] = {}
        self._startup_lock: threading.Lock = threading.Lock()

    def _ensure_loop_running(self) -> None:
        """Start the background event loop thread if not already running."""
        with self._startup_lock:
            if self._thread is not None and self._thread.is_alive():
                return

            import asyncio

            def run_loop() -> None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._lifespan_receive_queue = asyncio.Queue()
                self._async_adapter = AsyncServerGatewayInterface(
                    self.app,
                    raise_app_exceptions=self.raise_app_exceptions,
                    max_retries=self.max_retries,
                    lifespan_state=self._lifespan_state,
                )
                # Start lifespan handler
                self._lifespan_task = self._loop.create_task(self._handle_lifespan())
                self._started.set()
                self._loop.run_forever()

            self._thread = threading.Thread(target=run_loop, daemon=True)
            self._thread.start()
            self._started.wait()
            self._lifespan_startup_complete.wait()

            if self._lifespan_startup_failed is not None:
                raise self._lifespan_startup_failed

    async def _handle_lifespan(self) -> None:
        """Handle ASGI lifespan protocol."""
        scope = {
            "type": "lifespan",
            "asgi": {"version": "3.0"},
            "state": self._lifespan_state,
        }

        startup_complete = asyncio.Event()
        shutdown_complete = asyncio.Event()
        startup_failed: list[Exception] = []

        # Keep local reference to avoid race condition during shutdown
        receive_queue = self._lifespan_receive_queue

        async def receive() -> ASGIMessage:
            return await receive_queue.get()  # type: ignore[union-attr]

        async def send(message: ASGIMessage) -> None:
            if message["type"] == "lifespan.startup.complete":
                startup_complete.set()
            elif message["type"] == "lifespan.startup.failed":
                startup_failed.append(RuntimeError(message.get("message", "Lifespan startup failed")))
                startup_complete.set()
            elif message["type"] == "lifespan.shutdown.complete":
                shutdown_complete.set()
            elif message["type"] == "lifespan.shutdown.failed":
                shutdown_complete.set()

        async def run_lifespan() -> None:
            try:
                await self.app(scope, receive, send)
            except Exception as e:
                if not startup_complete.is_set():
                    startup_failed.append(e)
                    startup_complete.set()

        lifespan_task = asyncio.create_task(run_lifespan())

        # Send startup event
        await receive_queue.put({"type": "lifespan.startup"})  # type: ignore[union-attr]
        await startup_complete.wait()

        if startup_failed:
            self._lifespan_startup_failed = startup_failed[0]
        self._lifespan_startup_complete.set()

        # Wait for shutdown signal (loop.stop() will cancel this)
        try:
            await asyncio.Future()  # Wait forever until canceled
        except (asyncio.CancelledError, GeneratorExit):
            pass

        # Send shutdown event - must happen before loop stops
        if receive_queue is not None:
            try:
                await receive_queue.put({"type": "lifespan.shutdown"})
                await asyncio.wait_for(shutdown_complete.wait(), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, RuntimeError):
                pass
        lifespan_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await lifespan_task

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
        """Send a PreparedRequest to the ASGI application synchronously."""
        if stream:
            raise ValueError(
                "ThreadAsyncServerGatewayInterface does not support streaming responses. "
                "Use stream=False or migrate to pure async/await implementation."
            )

        self._ensure_loop_running()

        future: Future[Response] = Future()

        async def run_send() -> None:
            try:
                result = await self._async_adapter.send(  # type: ignore[union-attr]
                    request,
                    stream=False,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies,
                )
                _swap_context(result)
                future.set_result(result)  # type: ignore[arg-type]
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(run_send()))

        return future.result()

    def close(self) -> None:
        """Clean up adapter resources."""
        if self._loop is not None and self._lifespan_task is not None:
            # Signal shutdown and wait for it to complete
            shutdown_done = threading.Event()

            async def do_shutdown() -> None:
                if self._lifespan_task is not None:
                    self._lifespan_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._lifespan_task
                shutdown_done.set()

            self._loop.call_soon_threadsafe(lambda: self._loop.create_task(do_shutdown()))
            shutdown_done.wait(timeout=6.0)

        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        # Clear resources only after thread has stopped
        self._loop = None
        self._async_adapter = None
        self._lifespan_task = None
        self._lifespan_receive_queue = None
        self._started.clear()
        self._lifespan_startup_complete.clear()
        self._lifespan_startup_failed = None


__all__ = ("AsyncServerGatewayInterface", "ThreadAsyncServerGatewayInterface")
