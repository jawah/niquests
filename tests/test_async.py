from __future__ import annotations

import asyncio

import pytest

from niquests import AsyncSession


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.asyncio
class TestAsyncWithoutMultiplex:
    async def test_awaitable_get(self):
        async with AsyncSession() as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is False
            assert resp.status_code == 200

    async def test_concurrent_task_get(self):
        async def emit():
            responses = []

            async with AsyncSession() as s:
                responses.append(await s.get("https://pie.dev/get"))
                responses.append(await s.get("https://pie.dev/delay/5"))

            return responses

        foo = asyncio.create_task(emit())
        bar = asyncio.create_task(emit())

        responses_foo = await foo
        responses_bar = await bar

        assert len(responses_foo) == 2
        assert len(responses_bar) == 2

        assert all(r.status_code == 200 for r in responses_foo + responses_bar)


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.asyncio
class TestAsyncWithMultiplex:
    async def test_awaitable_get(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is True
            await s.gather()

            assert resp.status_code == 200

    async def test_awaitable_get_direct_access_lazy(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is True
            assert resp.status_code == 200

    async def test_concurrent_task_get(self):
        async def emit():
            responses = []

            async with AsyncSession(multiplexed=True) as s:
                responses.append(await s.get("https://pie.dev/get"))
                responses.append(await s.get("https://pie.dev/delay/5"))

                await s.gather()

            return responses

        foo = asyncio.create_task(emit())
        bar = asyncio.create_task(emit())

        responses_foo = await foo
        responses_bar = await bar

        assert len(responses_foo) == 2
        assert len(responses_bar) == 2

        assert all(r.status_code == 200 for r in responses_foo + responses_bar)
