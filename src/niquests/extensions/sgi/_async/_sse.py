from __future__ import annotations

import asyncio
import contextlib
import typing

from ....packages.urllib3.contrib.webextensions._async.sse import AsyncServerSideEventExtensionFromHTTP
from ....packages.urllib3.contrib.webextensions.sse import ServerSentEvent


class ASGISSEExtension(AsyncServerSideEventExtensionFromHTTP):
    """Async SSE extension for ASGI applications.

    Runs the ASGI app as a normal HTTP streaming request and parses
    SSE events from the response body chunks.
    """

    def __init__(self) -> None:
        self._closed = False
        self._buffer: str = ""
        self._last_event_id: str | None = None
        self._response_queue: asyncio.Queue[dict[str, typing.Any] | None] | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(  # type: ignore[override]
        self,
        app: typing.Any,
        scope: dict[str, typing.Any],
        body: bytes = b"",
    ) -> dict[str, typing.Any]:
        """Start the ASGI app and wait for http.response.start.

        Returns the response start message (with status and headers).
        """
        self._response_queue = asyncio.Queue()

        request_complete = False
        response_complete = asyncio.Event()

        async def receive() -> dict[str, typing.Any]:
            nonlocal request_complete
            if request_complete:
                await response_complete.wait()
                return {"type": "http.disconnect"}
            request_complete = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, typing.Any]) -> None:
            await self._response_queue.put(message)  # type: ignore[union-attr]
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_complete.set()

        async def run_app() -> None:
            try:
                await app(scope, receive, send)
            finally:
                await self._response_queue.put(None)  # type: ignore[union-attr]

        self._task = asyncio.create_task(run_app())

        # Wait for http.response.start
        while True:
            message = await self._response_queue.get()
            if message is None:
                raise ConnectionError("ASGI app closed before sending response headers")
            if message["type"] == "http.response.start":
                return message

    @property
    def closed(self) -> bool:
        return self._closed

    async def next_payload(self, *, raw: bool = False) -> ServerSentEvent | str | None:
        """Read and parse the next SSE event from the ASGI response stream.
        Returns None when the stream ends."""
        if self._closed:
            raise OSError("The SSE extension is closed")

        while True:
            # Check if we already have a complete event in the buffer
            sep_idx = self._buffer.find("\n\n")
            if sep_idx == -1:
                sep_idx = self._buffer.find("\r\n\r\n")
                if sep_idx != -1:
                    sep_len = 4
                else:
                    sep_len = 2
            else:
                sep_len = 2

            if sep_idx != -1:
                raw_event = self._buffer[:sep_idx]
                self._buffer = self._buffer[sep_idx + sep_len :]

                event = self._parse_event(raw_event)

                if event is not None:
                    if raw:
                        return raw_event + "\n\n"
                    return event

                # Empty event (e.g. just comments), try next
                continue

            # Need more data from the ASGI response queue
            chunk = await self._read_chunk()
            if chunk is None:
                self._closed = True
                return None

            self._buffer += chunk

    async def _read_chunk(self) -> str | None:
        """Read the next body chunk from the ASGI response."""
        if self._response_queue is None:
            return None

        message = await self._response_queue.get()
        if message is None:
            return None
        if message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                return body.decode("utf-8")
        return None

    def _parse_event(self, raw_event: str) -> ServerSentEvent | None:
        """Parse a raw SSE event block into a ServerSentEvent."""
        kwargs: dict[str, typing.Any] = {}

        for line in raw_event.splitlines():
            if not line or line.startswith(":"):
                continue
            key, _, value = line.partition(":")
            if key not in {"event", "data", "retry", "id"}:
                continue
            if value.startswith(" "):
                value = value[1:]
            if key == "id":
                if "\u0000" in value:
                    continue
            if key == "retry":
                try:
                    value = int(value)  # type: ignore[assignment]
                except (ValueError, TypeError):
                    continue
            kwargs[key] = value

        if not kwargs:
            return None

        if "id" not in kwargs and self._last_event_id is not None:
            kwargs["id"] = self._last_event_id

        event = ServerSentEvent(**kwargs)

        if event.id:
            self._last_event_id = event.id

        return event

    async def close(self) -> None:
        """Close the SSE stream and clean up the app task."""
        if self._closed:
            return

        self._closed = True

        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
