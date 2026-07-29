from __future__ import annotations

import codecs
import typing

from ...packages.urllib3.contrib.webextensions.sse import ServerSentEvent, ServerSideEventExtensionFromHTTP


class WASISSEExtension(ServerSideEventExtensionFromHTTP):
    def __init__(self, raw: typing.Any) -> None:
        self._raw = raw
        self._closed = False
        self._buffer = ""
        self._last_event_id: str | None = None
        self._decoder = codecs.getincrementaldecoder("utf-8")()

    @property
    def closed(self) -> bool:
        return self._closed

    def next_payload(self, *, raw: bool = False) -> ServerSentEvent | str | None:
        if self._closed:
            raise OSError("The SSE extension is closed")
        while True:
            lf = self._buffer.find("\n\n")
            crlf = self._buffer.find("\r\n\r\n")
            if lf >= 0 or crlf >= 0:
                if crlf >= 0 and (lf < 0 or crlf < lf):
                    boundary, separator = crlf, "\r\n\r\n"
                else:
                    boundary, separator = lf, "\n\n"
                block = self._buffer[:boundary]
                self._buffer = self._buffer[boundary + len(separator) :]
                event = self._parse_event(block)
                if event is not None:
                    return block + "\n\n" if raw else event
                continue
            chunk = self._raw.read(16 * 1024)
            if not chunk:
                self._buffer += self._decoder.decode(b"", final=True)
                self._closed = True
                return None
            self._buffer += self._decoder.decode(chunk)

    def _parse_event(self, block: str) -> ServerSentEvent | None:
        values: dict[str, typing.Any] = {}
        data: list[str] = []
        for line in block.splitlines():
            if not line or line.startswith(":"):
                continue
            key, _, value = line.partition(":")
            if value.startswith(" "):
                value = value[1:]
            if key == "data":
                data.append(value)
            elif key == "id" and "\0" not in value:
                values[key] = value
            elif key == "retry":
                try:
                    values[key] = int(value)
                except ValueError:
                    pass
            elif key == "event":
                values[key] = value
        if data:
            values["data"] = "\n".join(data)
        if not values:
            return None
        if "id" not in values and self._last_event_id is not None:
            values["id"] = self._last_event_id
        event = ServerSentEvent(**values)
        if event.id:
            self._last_event_id = event.id
        return event

    def start(self, response: typing.Any) -> None:
        raise NotImplementedError

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._raw.close()
