from __future__ import annotations

import pytest

from niquests import Session, AsyncSession

try:
    import wsproto
except ImportError:
    wsproto = None


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.skipif(wsproto is None, reason="wsproto unavailable")
class TestLiveWebSocket:
    def test_sync_websocket_basic_example(self) -> None:
        with Session() as s:
            resp = s.get("wss://echo.websocket.org")

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False

            greeting_msg = resp.extension.next_payload()

            assert greeting_msg is not None
            assert isinstance(greeting_msg, str)

            resp.extension.send_payload("Hello World")
            resp.extension.send_payload(b"Foo Bar Baz!")

            assert resp.extension.next_payload() == "Hello World"
            assert resp.extension.next_payload() == b"Foo Bar Baz!"

            resp.extension.close()
            assert resp.extension.closed is True

    @pytest.mark.asyncio
    async def test_async_websocket_basic_example(self) -> None:
        async with AsyncSession() as s:
            resp = await s.get("wss://echo.websocket.org")

            assert resp.status_code == 101
            assert resp.extension is not None
            assert resp.extension.closed is False

            greeting_msg = await resp.extension.next_payload()

            assert greeting_msg is not None
            assert isinstance(greeting_msg, str)

            await resp.extension.send_payload("Hello World")
            await resp.extension.send_payload(b"Foo Bar Baz!")

            assert (await resp.extension.next_payload()) == "Hello World"
            assert (await resp.extension.next_payload()) == b"Foo Bar Baz!"

            await resp.extension.close()
            assert resp.extension.closed is True
