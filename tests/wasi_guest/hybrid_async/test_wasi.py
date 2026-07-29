from __future__ import annotations

import niquests
from niquests.adapters import AsyncHTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities
from niquests.extensions.wasi._async._adapter import AsyncWASIAdapter


async def test_hybrid_selection_and_requests() -> None:
    async with niquests.AsyncSession() as session:
        assert capabilities.HAS_WASI_P3_SOCKETS
        assert capabilities.HAS_WASI_P3_HTTP
        assert not capabilities.HAS_WASI_TLS_SUPPORT
        assert isinstance(session.get_adapter("http://httpbingo.org"), AsyncHTTPAdapter)
        assert isinstance(session.get_adapter("https://httpbingo.org"), AsyncWASIAdapter)
        assert (await session.get("http://httpbingo.org/get")).status_code == 200
        assert (await session.get("https://httpbingo.org/get")).status_code == 200


CASES = {"hybrid-selection-and-requests": test_hybrid_selection_and_requests}
