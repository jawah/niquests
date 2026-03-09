from __future__ import annotations

import asyncio
import contextlib
import typing


class ASGIWebSocketExtension:
    """Async WebSocket extension for ASGI applications.

    Uses the ASGI websocket protocol with send/receive queues to communicate
    with the application task.
    """

    def __init__(self) -> None:
        self._closed = False
        self._app_send_queue: asyncio.Queue[dict[str, typing.Any]] = asyncio.Queue()
        self._app_receive_queue: asyncio.Queue[dict[str, typing.Any]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def start(self, app: typing.Any, scope: dict[str, typing.Any]) -> None:
        """Start the ASGI app task and perform the WebSocket handshake."""

        async def receive() -> dict[str, typing.Any]:
            return await self._app_receive_queue.get()

        async def send(message: dict[str, typing.Any]) -> None:
            await self._app_send_queue.put(message)

        self._task = asyncio.create_task(app(scope, receive, send))

        # Send connect and wait for accept
        await self._app_receive_queue.put({"type": "websocket.connect"})

        message = await self._app_send_queue.get()

        if message["type"] == "websocket.close":
            self._closed = True
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            raise ConnectionError(f"WebSocket connection rejected with code {message.get('code', 1000)}")

        if message["type"] != "websocket.accept":
            self._closed = True
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            raise ConnectionError(f"Unexpected ASGI message during handshake: {message['type']}")

    @property
    def closed(self) -> bool:
        return self._closed

    async def next_payload(self) -> str | bytes | None:
        """Await the next message from the ASGI WebSocket app.
        Returns None when the app closes the connection."""
        if self._closed:
            raise OSError("The WebSocket extension is closed")

        message = await self._app_send_queue.get()

        if message["type"] == "websocket.send":
            if "text" in message:
                return message["text"]
            if "bytes" in message:
                return message["bytes"]
            return b""

        if message["type"] == "websocket.close":
            self._closed = True
            return None

        return None

    async def send_payload(self, buf: str | bytes) -> None:
        """Send a message to the ASGI WebSocket app."""
        if self._closed:
            raise OSError("The WebSocket extension is closed")

        if isinstance(buf, (bytes, bytearray)):
            await self._app_receive_queue.put({"type": "websocket.receive", "bytes": bytes(buf)})
        else:
            await self._app_receive_queue.put({"type": "websocket.receive", "text": buf})

    async def close(self) -> None:
        """Close the WebSocket and clean up the app task."""
        if self._closed:
            return

        self._closed = True

        await self._app_receive_queue.put({"type": "websocket.disconnect", "code": 1000})

        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
