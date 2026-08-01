from __future__ import annotations

import pytest

from niquests import AsyncSession, ReadTimeout, Session

try:
    import wsproto
except ImportError:
    wsproto = None


@pytest.mark.usefixtures("requires_traefik_tls")
@pytest.mark.skipif(wsproto is None, reason="wsproto unavailable")
class TestLiveWebSocket:
    def test_sync_websocket_basic_example(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        with Session(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = s.get(local_httpbin.websocket_url, verify=traefik_ca_bundle)

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False

            # greeting_msg = resp.extension.next_payload()
            #
            # assert greeting_msg is not None
            # assert isinstance(greeting_msg, str)

            resp.extension.send_payload("Hello World")
            resp.extension.send_payload(b"Foo Bar Baz!")

            assert resp.extension.next_payload() == "Hello World"
            assert resp.extension.next_payload() == b"Foo Bar Baz!"

            resp.extension.close()
            assert resp.extension.closed is True

    @pytest.mark.asyncio
    async def test_async_websocket_basic_example(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        async with AsyncSession(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = await s.get(local_httpbin.websocket_url, verify=traefik_ca_bundle)

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False

            # greeting_msg = await resp.extension.next_payload()
            #
            # assert greeting_msg is not None
            # assert isinstance(greeting_msg, str)

            await resp.extension.send_payload("Hello World")
            await resp.extension.send_payload(b"Foo Bar Baz!")

            assert (await resp.extension.next_payload()) == "Hello World"
            assert (await resp.extension.next_payload()) == b"Foo Bar Baz!"

            await resp.extension.close()
            assert resp.extension.closed is True

    def test_sync_websocket_read_timeout(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        with Session(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = s.get(local_httpbin.websocket_url, timeout=3, verify=traefik_ca_bundle)

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False

            # greeting_msg = resp.extension.next_payload()
            #
            # assert greeting_msg is not None
            # assert isinstance(greeting_msg, str)

            with pytest.raises(ReadTimeout):
                resp.extension.next_payload()

            resp.extension.close()
            assert resp.extension.closed is True

    @pytest.mark.asyncio
    async def test_async_websocket_read_timeout(self, local_httpbin, traefik_resolver, traefik_ca_bundle) -> None:
        async with AsyncSession(resolver=traefik_resolver, verify=traefik_ca_bundle) as s:
            resp = await s.get(local_httpbin.websocket_url, timeout=3, verify=traefik_ca_bundle)

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False
            #
            # greeting_msg = await resp.extension.next_payload()
            #
            # assert greeting_msg is not None
            # assert isinstance(greeting_msg, str)

            with pytest.raises(ReadTimeout):
                await resp.extension.next_payload()

            await resp.extension.close()
            assert resp.extension.closed is True
