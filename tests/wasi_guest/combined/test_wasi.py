from __future__ import annotations

import niquests
from niquests.extensions.wasi import _capabilities as capabilities


async def test_combined_world_capabilities_and_requests() -> None:
    assert capabilities.HAS_WASI_P2_SOCKETS
    assert capabilities.HAS_WASI_P3_SOCKETS
    assert capabilities.HAS_WASI_P2_HTTP
    assert capabilities.HAS_WASI_P3_HTTP
    assert capabilities.HAS_WASI_TLS_SUPPORT
    resolver = "in-memory://default?hosts=httpbin.local:127.0.0.1"
    async with niquests.AsyncSession(resolver=resolver, verify="/workspace/rootCA.pem") as async_session:
        assert (await async_session.get("https://httpbin.local:4443/get")).status_code == 200
    with niquests.Session(resolver=resolver, verify="/workspace/rootCA.pem") as session:
        assert session.get("https://httpbin.local:4443/get").status_code == 200


CASES = {"combined-world-capabilities-and-requests": test_combined_world_capabilities_and_requests}
