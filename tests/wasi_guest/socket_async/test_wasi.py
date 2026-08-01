from __future__ import annotations

import asyncio

import niquests
from niquests.adapters import AsyncHTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities

HTTPS_URL = "https://httpbin.local:4443"
ROOT_CA = "/workspace/rootCA.pem"
RESOLVER = "in-memory://default?hosts=httpbin.local:127.0.0.1"


async def test_capabilities_and_adapter_selection() -> None:
    async with niquests.AsyncSession(resolver=RESOLVER, verify=ROOT_CA) as session:
        assert capabilities.HAS_WASI_P3_SOCKETS
        assert not capabilities.HAS_WASI_P3_HTTP
        assert capabilities.HAS_WASI_TLS_SUPPORT
        assert isinstance(session.get_adapter(HTTPS_URL), AsyncHTTPAdapter)


async def test_https_http2_and_concurrency() -> None:
    async with niquests.AsyncSession(resolver=RESOLVER, verify=ROOT_CA) as session:
        responses = await asyncio.gather(
            session.get(f"{HTTPS_URL}/get"),
            session.get(f"{HTTPS_URL}/get"),
        )
        assert all(response.status_code == 200 for response in responses)
        assert all(response.raw.version == 20 for response in responses)


async def test_real_http2_trailers() -> None:
    async with niquests.AsyncSession(resolver=RESOLVER, verify=ROOT_CA) as session:
        response = await session.get(f"{HTTPS_URL}/trailers?trailer1=value1&trailer2=value2")
        assert response.trailers == {"trailer1": "value1", "trailer2": "value2"}


async def test_redirect_chain_and_disabled_following() -> None:
    async with niquests.AsyncSession(resolver=RESOLVER, verify=ROOT_CA) as session:
        response = await session.get(f"{HTTPS_URL}/redirect/3")
        assert response.url.endswith("/get")
        assert len(response.history) == 3
        assert all(item.status_code == 302 for item in response.history)

        response = await session.get(f"{HTTPS_URL}/redirect/3", allow_redirects=False)
        assert response.status_code == 302
        assert not response.history


CASES = {
    "capabilities-and-adapter-selection": test_capabilities_and_adapter_selection,
    "https-http2-and-concurrency": test_https_http2_and_concurrency,
    "real-http2-trailers": test_real_http2_trailers,
    "redirect-chain-and-disabled-following": test_redirect_chain_and_disabled_following,
}
