from __future__ import annotations

import typing

from pyodide.ffi import run_sync  # type: ignore[import]
from pyodide.http import pyfetch  # type: ignore[import]

from ...packages.urllib3.contrib.webextensions.sse import ServerSentEvent


class PyodideSSEExtension:
    """SSE extension for Pyodide using pyfetch streaming + manual SSE parsing.

    Synchronous via JSPI (run_sync). Reads from a ReadableStream reader,
    buffers partial lines, and parses complete SSE events.
    """

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._closed = False
        self._buffer: str = ""
        self._last_event_id: str | None = None
        self._reader: typing.Any = None

        fetch_options: dict[str, typing.Any] = {
            "method": "GET",
            "headers": {
                "Accept": "text/event-stream",
                "Cache-Control": "no-store",
                **(headers or {}),
            },
        }

        js_response = run_sync(pyfetch(url, **fetch_options))

        body = js_response.js_response.body
        if body is not None:
            self._reader = body.getReader()

    @property
    def closed(self) -> bool:
        return self._closed

    def _read_chunk(self) -> str | None:
        """Read the next chunk from the ReadableStream, blocking via JSPI."""
        if self._reader is None:
            return None

        try:
            result = run_sync(self._reader.read())
            if result.done:
                return None
            value = result.value
            if value is not None:
                return bytes(value.to_py()).decode("utf-8")
            return None
        except Exception:
            return None

    def next_payload(self, *, raw: bool = False) -> ServerSentEvent | str | None:
        """Read and parse the next SSE event from the stream.
        Returns None when the stream ends."""
        if self._closed:
            raise OSError("The SSE extension is closed")

        # Keep reading chunks until we have a complete event (double newline)
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

    def send_payload(self, buf: str | bytes) -> None:
        """SSE is one-way only."""
        raise NotImplementedError("SSE is only one-way. Sending is forbidden.")

    def close(self) -> None:
        """Close the stream and release resources."""
        if self._closed:
            return

        self._closed = True

        if self._reader is not None:
            try:
                run_sync(self._reader.cancel())
            except Exception:
                pass
            self._reader = None
