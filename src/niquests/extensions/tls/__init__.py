from __future__ import annotations

import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from ...packages.urllib3.contrib.anytls import ssl


@dataclass
class TLSConfiguration:
    backend: typing.Literal["utls", "rtls", "ssl"] | None = None
    min_version: ssl.TLSVersion | None = None
    max_version: ssl.TLSVersion | None = None
    ciphers: str | None = None


__all__ = ("TLSConfiguration",)
