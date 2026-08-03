from __future__ import annotations

import pytest

from niquests import AsyncSession, Session


@pytest.mark.usefixtures("requires_traefik_tls")
class TestLiveSSE:
    def test_sync_sse_basic_example(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        with Session(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = s.get(local_httpbin.sse_url, verify=traefik_ca_bundle)

            assert resp.status_code == 200
            assert resp.extension is not None
            assert resp.extension.closed is False

            events = []

            while resp.extension.closed is False:
                events.append(resp.extension.next_payload())

            assert resp.extension.closed is True
            assert len(events) > 0
            assert events[-1] is None

    @pytest.mark.asyncio
    async def test_async_sse_basic_example(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        async with AsyncSession(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = await s.get(local_httpbin.sse_url, verify=traefik_ca_bundle)

            assert resp.status_code == 200
            assert resp.extension is not None
            assert resp.extension.closed is False

            events = []

            while resp.extension.closed is False:
                events.append(await resp.extension.next_payload())

            assert resp.extension.closed is True
            assert len(events) > 0
            assert events[-1] is None
