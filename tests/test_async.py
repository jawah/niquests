from __future__ import annotations

import asyncio
import json
import os

import pytest

from niquests import AsyncSession, AsyncResponse, Response
from niquests.exceptions import MultiplexingError


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.asyncio
class TestAsyncWithoutMultiplex:
    async def test_awaitable_get(self):
        async with AsyncSession() as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is False
            assert resp.status_code == 200

    async def test_awaitable_redirect_chain(self):
        async with AsyncSession() as s:
            resp = await s.get("https://pie.dev/redirect/2")

            assert resp.lazy is False
            assert resp.status_code == 200

    async def test_awaitable_redirect_chain_stream(self):
        async with AsyncSession() as s:
            resp = await s.get("https://pie.dev/redirect/2", stream=True)

            assert resp.lazy is False
            assert resp.status_code == 200
            assert await resp.json()

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

    async def test_with_async_iterable(self):
        async with AsyncSession() as s:

            async def fake_aiter():
                await asyncio.sleep(0.01)
                yield b"foo"
                await asyncio.sleep(0.01)
                yield b"bar"

            r = await s.post("https://pie.dev/post", data=fake_aiter())

            assert r.status_code == 200
            assert r.json()["data"] == "foobar"

    async def test_with_async_auth(self):
        async with AsyncSession() as s:

            async def fake_aauth(p):
                await asyncio.sleep(0.01)
                p.headers["X-Async-Auth"] = "foobar"
                return p

            r = await s.get("https://pie.dev/get", auth=fake_aauth)

            assert r.status_code == 200
            assert "X-Async-Auth" in r.json()["headers"]


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.asyncio
class TestAsyncWithMultiplex:
    async def test_awaitable_get(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is True
            await s.gather()
            assert resp.status_code == 200

    async def test_awaitable_redirect_with_lazy(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/redirect/3")

            assert resp.lazy is True
            await s.gather()
            assert resp.status_code == 200

    async def test_awaitable_redirect_direct_access_with_lazy(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/redirect/3")

            assert resp.lazy is True

            with pytest.raises(MultiplexingError):
                resp.status_code

            await s.gather(resp)

            assert resp.status_code == 200
            assert len(resp.history) == 3
            assert all(isinstance(_, Response) for _ in resp.history)

    async def test_awaitable_stream_redirect_direct_access_with_lazy(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/redirect/3", stream=True)

            assert isinstance(resp, AsyncResponse)
            assert resp.lazy is True

            await resp.json()

            assert resp.lazy is False

            assert resp.status_code == 200
            assert len(resp.history) == 3
            assert all(isinstance(_, Response) for _ in resp.history)

    async def test_awaitable_get_direct_access_lazy(self):
        async with AsyncSession(multiplexed=True) as s:
            resp = await s.get("https://pie.dev/get")

            assert resp.lazy is True
            assert isinstance(resp, Response)

            with pytest.raises(MultiplexingError):
                resp.status_code == 200

            await s.gather(resp)
            assert resp.status_code == 200

            resp = await s.get("https://pie.dev/get", stream=True)

            assert isinstance(resp, AsyncResponse)

            with pytest.raises(MultiplexingError):
                resp.status_code

            await resp.content
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

    async def test_with_stream_json(self):
        async with AsyncSession() as s:
            r = await s.get("https://pie.dev/get", stream=True)
            assert isinstance(r, AsyncResponse)
            assert r.ok
            payload = await r.json()
            assert payload

    async def test_with_stream_text(self):
        async with AsyncSession() as s:
            r = await s.get("https://pie.dev/get", stream=True)
            assert isinstance(r, AsyncResponse)
            assert r.ok
            payload = await r.text
            assert payload is not None

    async def test_with_stream_iter_decode(self):
        async with AsyncSession() as s:
            r = await s.get("https://pie.dev/get", stream=True)
            assert isinstance(r, AsyncResponse)
            assert r.ok
            payload = ""

            async for chunk in await r.iter_content(16, decode_unicode=True):
                payload += chunk

            assert json.loads(payload)

    async def test_with_stream_iter_raw(self):
        async with AsyncSession() as s:
            r = await s.get("https://pie.dev/get", stream=True)
            assert isinstance(r, AsyncResponse)
            assert r.ok
            payload = b""

            async for chunk in await r.iter_content(16):
                payload += chunk

            assert json.loads(payload.decode())

    async def test_concurrent_task_get_with_stream(self):
        async def emit():
            responses = []

            async with AsyncSession(multiplexed=True) as s:
                responses.append(await s.get("https://pie.dev/get", stream=True))
                responses.append(await s.get("https://pie.dev/delay/5", stream=True))

                await s.gather()

                for response in responses:
                    await response.content

            return responses

        foo = asyncio.create_task(emit())
        bar = asyncio.create_task(emit())

        responses_foo = await foo
        responses_bar = await bar

        assert len(responses_foo) == 2
        assert len(responses_bar) == 2

        assert all(r.status_code == 200 for r in responses_foo + responses_bar)

    @pytest.mark.skipif(os.environ.get("CI") is None, reason="Worth nothing locally")
    async def test_happy_eyeballs(self) -> None:
        """A bit of context, this test, running it locally does not get us
        any confidence about Happy Eyeballs. This test is valuable in Github CI where IPv6 addresses are unreachable.
        We're using a custom DNS resolver that will yield the IPv6 addresses and IPv4 ones.
        If this hang in CI, then you did something wrong...!"""
        async with AsyncSession(resolver="doh+cloudflare://", happy_eyeballs=True) as s:
            r = await s.get("https://pie.dev/get")

            assert r.ok
