from __future__ import annotations

import asyncio
import typing

from pyodide.ffi import create_proxy  # type: ignore[import]

try:
    from js import WebSocket as JSWebSocket  # type: ignore[import]
except ImportError:
    JSWebSocket = None


class AsyncPyodideWebSocketExtension:
    """Async WebSocket extension for Pyodide using the browser's native WebSocket API.

    Messages are queued from JS callbacks and dequeued by next_payload()
    which awaits until a message arrives.
    """

    def __init__(self) -> None:
        self._closed = False
        self._queue: asyncio.Queue[str | bytes | None] = asyncio.Queue()
        self._proxies: list[typing.Any] = []
        self._ws: typing.Any = None

    async def start(self, url: str) -> None:
        """Open the WebSocket connection and wait until it's ready."""
        if JSWebSocket is None:  # Defensive: depends on JS runtime
            raise OSError(
                "WebSocket is not available in this JavaScript runtime. "
                "Browser environment required (not supported in Node.js)."
            )

        loop = asyncio.get_running_loop()
        open_future: asyncio.Future[None] = loop.create_future()

        self._ws = JSWebSocket.new(url)
        self._ws.binaryType = "arraybuffer"

        # JS→Python callbacks: invoked by the browser event loop, not Python call
        # frames, so coverage cannot trace into them.
        def _onopen(event: typing.Any) -> None:  # Defensive: JS callback
            if not open_future.done():
                open_future.set_result(None)

        def _onerror(event: typing.Any) -> None:  # Defensive: JS callback
            if not open_future.done():
                open_future.set_exception(ConnectionError("WebSocket connection failed"))

        def _onmessage(event: typing.Any) -> None:  # Defensive: JS callback
            data = event.data
            if isinstance(data, str):
                self._queue.put_nowait(data)
            else:
                # ArrayBuffer → bytes via Pyodide
                self._queue.put_nowait(bytes(data.to_py()))

        def _onclose(event: typing.Any) -> None:  # Defensive: JS callback
            self._queue.put_nowait(None)

        for name, fn in [
            ("onopen", _onopen),
            ("onerror", _onerror),
            ("onmessage", _onmessage),
            ("onclose", _onclose),
        ]:
            proxy = create_proxy(fn)
            self._proxies.append(proxy)
            setattr(self._ws, name, proxy)

        await open_future

    @property
    def closed(self) -> bool:
        return self._closed

    async def next_payload(self) -> str | bytes | None:
        """Await the next message from the WebSocket.
        Returns None when the remote end closes the connection."""
        if self._closed:  # Defensive: caller should not call after close
            raise OSError("The WebSocket extension is closed")

        msg = await self._queue.get()

        if msg is None:  # Defensive: server-initiated close sentinel
            self._closed = True

        return msg

    async def send_payload(self, buf: str | bytes) -> None:
        """Send a message over the WebSocket."""
        if self._closed:  # Defensive: caller should not call after close
            raise OSError("The WebSocket extension is closed")

        if isinstance(buf, (bytes, bytearray)):
            from js import Uint8Array  # type: ignore[import]

            self._ws.send(Uint8Array.new(buf))
        else:
            self._ws.send(buf)

    async def ping(self) -> None:
        """No-op — browser WebSocket handles ping/pong at protocol level."""
        pass

    async def close(self) -> None:
        """Close the WebSocket and clean up proxies."""
        if self._closed:  # Defensive: idempotent close
            return

        self._closed = True

        try:
            self._ws.close()
        except Exception:  # Defensive: suppress JS errors on teardown
            pass

        for proxy in self._proxies:
            try:
                proxy.destroy()
            except Exception:  # Defensive: suppress JS errors on teardown
                pass
        self._proxies.clear()
