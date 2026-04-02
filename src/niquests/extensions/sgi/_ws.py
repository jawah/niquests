from __future__ import annotations

import typing
from concurrent.futures import Future

try:
    from ...packages.urllib3.contrib.webextensions.ws import WebSocketExtensionFromHTTP
except ImportError:
    from ...packages.urllib3.contrib.webextensions.raw import RawExtensionFromHTTP as WebSocketExtensionFromHTTP

if typing.TYPE_CHECKING:
    import asyncio

    from ...packages.urllib3 import HTTPResponse
    from ._async._ws import ASGIWebSocketExtension


class ThreadASGIWebSocketExtension(WebSocketExtensionFromHTTP):
    """Synchronous WebSocket extension wrapping an async ASGIWebSocketExtension.

    Delegates all operations to the async extension on a background event loop,
    blocking the calling thread via concurrent.futures.Future.
    """

    def __init__(self, async_ext: ASGIWebSocketExtension, loop: asyncio.AbstractEventLoop) -> None:
        self._async_ext = async_ext
        self._loop = loop

    def start(self, response: HTTPResponse) -> None:
        raise NotImplementedError

    @property
    def closed(self) -> bool:
        return self._async_ext.closed

    def next_payload(self) -> str | bytes | None:
        """Block until the next message arrives from the ASGI WebSocket app."""
        future: Future[str | bytes | None] = Future()

        async def _do() -> None:
            try:
                result = await self._async_ext.next_payload()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_do()))
        return future.result()

    def send_payload(self, buf: str | bytes) -> None:
        """Send a message to the ASGI WebSocket app."""
        future: Future[None] = Future()

        async def _do() -> None:
            try:
                await self._async_ext.send_payload(buf)
                future.set_result(None)
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_do()))
        future.result()

    def close(self) -> None:
        """Close the WebSocket and clean up."""
        future: Future[None] = Future()

        async def _do() -> None:
            try:
                await self._async_ext.close()
                future.set_result(None)
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_do()))
        future.result()
