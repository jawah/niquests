from __future__ import annotations

import typing
from concurrent.futures import Future

from ...packages.urllib3.contrib.webextensions.sse import ServerSentEvent, ServerSideEventExtensionFromHTTP

if typing.TYPE_CHECKING:
    import asyncio

    from ...packages.urllib3 import HTTPResponse
    from ._async._sse import ASGISSEExtension


class WSGISSEExtension(ServerSideEventExtensionFromHTTP):
    """SSE extension for WSGI applications.

    Reads from a WSGI response iterator, buffers text, and parses SSE events.
    """

    def __init__(self, generator: typing.Generator[bytes, None, None]) -> None:
        self._generator = generator
        self._closed = False
        self._buffer: str = ""
        self._last_event_id: str | None = None

    @property
    def closed(self) -> bool:
        return self._closed

    def next_payload(self, *, raw: bool = False) -> ServerSentEvent | str | None:
        """Read and parse the next SSE event from the WSGI response.
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

            # Need more data
            chunk = self._read_chunk()
            if chunk is None:
                self._closed = True
                return None

            self._buffer += chunk

    def _read_chunk(self) -> str | None:
        """Read the next chunk from the WSGI response iterator."""
        try:
            chunk = next(self._generator)
            if chunk:
                return chunk.decode("utf-8")
            return None
        except StopIteration:
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

    def close(self) -> None:
        """Close the stream and release resources."""
        if self._closed:
            return

        self._closed = True

        if hasattr(self._generator, "close"):
            self._generator.close()

    def start(self, response: HTTPResponse) -> None:
        raise NotImplementedError


class ThreadASGISSEExtension(ServerSideEventExtensionFromHTTP):
    """Synchronous SSE extension wrapping an async ASGISSEExtension.

    Delegates all operations to the async extension on a background event loop,
    blocking the calling thread via concurrent.futures.Future.
    """

    def __init__(self, async_ext: ASGISSEExtension, loop: asyncio.AbstractEventLoop) -> None:
        self._async_ext = async_ext
        self._loop = loop

    @property
    def closed(self) -> bool:
        return self._async_ext.closed

    def next_payload(self, *, raw: bool = False) -> ServerSentEvent | str | None:
        """Block until the next SSE event arrives from the ASGI app."""
        future: Future[ServerSentEvent | str | None] = Future()

        async def _do() -> None:
            try:
                result = await self._async_ext.next_payload(raw=raw)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_do()))
        return future.result()

    def start(self, response: HTTPResponse) -> None:
        raise NotImplementedError

    def close(self) -> None:
        """Close the SSE stream and clean up."""
        future: Future[None] = Future()

        async def _do() -> None:
            try:
                await self._async_ext.close()
                future.set_result(None)
            except Exception as e:
                future.set_exception(e)

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_do()))
        future.result()
