from __future__ import annotations

import pytest

from niquests import AsyncSession, Session


@pytest.mark.usefixtures("requires_wan")
class TestLiveSSE:
    def test_sync_sse_basic_example(self) -> None:
        with Session() as s:
            resp = s.get("sse://httpbingo.org/sse")

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
    async def test_async_sse_basic_example(self) -> None:
        async with AsyncSession() as s:
            resp = await s.get("sse://httpbingo.org/sse")

            assert resp.status_code == 200
            assert resp.extension is not None
            assert resp.extension.closed is False

            events = []

            while resp.extension.closed is False:
                events.append(await resp.extension.next_payload())

            assert resp.extension.closed is True
            assert len(events) > 0
            assert events[-1] is None
