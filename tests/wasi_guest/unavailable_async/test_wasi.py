from __future__ import annotations

import pytest

import niquests
from niquests.exceptions import InvalidSchema
from niquests.extensions.wasi import _capabilities as capabilities


async def test_async_capabilities_are_unavailable() -> None:
    assert not capabilities.HAS_WASI_P3_SOCKETS
    assert not capabilities.HAS_WASI_P3_HTTP
    with pytest.raises(InvalidSchema, match="No connection adapters were found"):
        await niquests.aget("http://httpbingo.org/get")
    with pytest.raises(ImportError):
        from niquests.extensions.wasi._async._adapter import AsyncWASIAdapter  # noqa: F401


CASES = {"async-capabilities-are-unavailable": test_async_capabilities_are_unavailable}
