from __future__ import annotations

import niquests
from niquests.extensions.wasi import _capabilities as capabilities


async def test_combined_world_capabilities_and_requests() -> None:
    assert capabilities.HAS_WASI_P2_SOCKETS
    assert capabilities.HAS_WASI_P3_SOCKETS
    assert capabilities.HAS_WASI_P2_HTTP
    assert capabilities.HAS_WASI_P3_HTTP
    assert capabilities.HAS_WASI_TLS_SUPPORT
    assert niquests.get("https://httpbingo.org/get").status_code == 200
    assert (await niquests.aget("https://httpbingo.org/get")).status_code == 200


CASES = {"combined-world-capabilities-and-requests": test_combined_world_capabilities_and_requests}
