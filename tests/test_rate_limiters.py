"""Tests for rate limiter hooks."""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from functools import partial

import pytest

import niquests
from niquests.hooks import (
    AsyncLeakyBucketLimiter,
    AsyncTokenBucketLimiter,
    LeakyBucketLimiter,
    TokenBucketLimiter,
)
from tests.testserver.server import Server


class TestSyncLimiters:
    """Tests for sync rate limiters."""

    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=10.0), id="token_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=10.0, capacity=20.0), id="token_bucket_with_capacity"),
        ],
    )
    def test_basic_request(self, limiter_factory):
        """Rate limiter should not prevent basic requests."""
        limiter = limiter_factory()
        with Server.basic_response_server() as (host, port):
            with niquests.Session(hooks=limiter) as session:
                response = session.get(f"http://{host}:{port}")
                assert response.status_code == 200

    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=10.0, capacity=10.0), id="token_bucket"),
        ],
    )
    def test_multiple_requests(self, limiter_factory):
        """Multiple requests should succeed with rate limiting."""
        limiter = limiter_factory()
        with Server.basic_response_server(requests_to_handle=3) as (host, port):
            with niquests.Session(hooks=limiter, headers={"Connection": "close"}) as session:
                for _ in range(3):
                    response = session.get(f"http://{host}:{port}")
                    assert response.status_code == 200

    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=20.0), id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=20.0, capacity=20.0), id="token_bucket"),
        ],
    )
    def test_thread_safety(self, limiter_factory):
        """Rate limiter should be thread-safe."""
        limiter = limiter_factory()
        results = []

        def make_request(session, url):
            response = session.get(url)
            return response.status_code

        with Server.basic_response_server(requests_to_handle=10) as (host, port):
            url = f"http://{host}:{port}"
            with niquests.Session(hooks=limiter, headers={"Connection": "close"}) as session:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(partial(make_request, session, url)) for _ in range(10)]
                    for future in concurrent.futures.as_completed(futures):
                        results.append(future.result())

        assert all(status == 200 for status in results)
        assert len(results) == 10

    def test_leaky_bucket_rate_limiting(self):
        """Verify leaky bucket introduces delays between requests."""
        rate = 5.0  # 5 requests per second = 200ms between requests
        limiter = LeakyBucketLimiter(rate=rate)
        with Server.basic_response_server(requests_to_handle=4) as (host, port):
            with niquests.Session(hooks=limiter, headers={"Connection": "close"}) as session:
                session.get(f"http://{host}:{port}")  # First request immediate

                start = time.monotonic()
                for _ in range(3):
                    session.get(f"http://{host}:{port}")
                elapsed = time.monotonic() - start

                expected_min = 3 * (1.0 / rate) * 0.8  # 80% tolerance
                assert elapsed >= expected_min

    def test_token_bucket_burst_capacity(self):
        """Token bucket should allow bursts up to capacity."""
        limiter = TokenBucketLimiter(rate=1.0, capacity=10.0)
        with Server.basic_response_server(requests_to_handle=5) as (host, port):
            with niquests.Session(hooks=limiter, headers={"Connection": "close"}) as session:
                start = time.monotonic()
                for _ in range(5):
                    response = session.get(f"http://{host}:{port}")
                    assert response.status_code == 200
                elapsed = time.monotonic() - start


                # Burst should be fast - with rate=1.0 and no burst, 5 requests
                # would take 4+ seconds. With burst capacity, it should be much faster.
                # Allow 5 seconds for network overhead.
                assert elapsed < 5.0


class TestAsyncLimiters:
    """Tests for async rate limiters."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=10.0), id="token_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=10.0, capacity=20.0), id="token_bucket_with_capacity"),
        ],
    )
    async def test_basic_request(self, limiter_factory):
        """Rate limiter should not prevent basic requests."""
        limiter = limiter_factory()
        with Server.basic_response_server() as (host, port):
            async with niquests.AsyncSession(hooks=limiter) as session:
                response = await session.get(f"http://{host}:{port}")
                assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=10.0, capacity=10.0), id="token_bucket"),
        ],
    )
    async def test_multiple_requests(self, limiter_factory):
        """Multiple requests should succeed with rate limiting."""
        limiter = limiter_factory()
        with Server.basic_response_server(requests_to_handle=3) as (host, port):
            async with niquests.AsyncSession(hooks=limiter, headers={"Connection": "close"}) as session:
                for _ in range(3):
                    response = await session.get(f"http://{host}:{port}")
                    assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=20.0), id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=20.0, capacity=20.0), id="token_bucket"),
        ],
    )
    async def test_concurrent_requests(self, limiter_factory):
        """Rate limiter should handle concurrent async requests."""
        limiter = limiter_factory()
        with Server.basic_response_server(requests_to_handle=10) as (host, port):
            url = f"http://{host}:{port}"
            async with niquests.AsyncSession(hooks=limiter, headers={"Connection": "close"}) as session:

                async def make_request():
                    response = await session.get(url)
                    return response.status_code

                tasks = [make_request() for _ in range(10)]
                results = await asyncio.gather(*tasks)

            assert all(status == 200 for status in results)
            assert len(results) == 10

    @pytest.mark.asyncio
    async def test_async_leaky_bucket_rate_limiting(self):
        """Verify async leaky bucket introduces delays between requests."""
        rate = 5.0
        limiter = AsyncLeakyBucketLimiter(rate=rate)
        with Server.basic_response_server(requests_to_handle=4) as (host, port):
            async with niquests.AsyncSession(hooks=limiter, headers={"Connection": "close"}) as session:
                await session.get(f"http://{host}:{port}")

                start = time.monotonic()
                for _ in range(3):
                    await session.get(f"http://{host}:{port}")
                elapsed = time.monotonic() - start

                expected_min = 3 * (1.0 / rate) * 0.8
                assert elapsed >= expected_min

    @pytest.mark.asyncio
    async def test_async_token_bucket_burst_capacity(self):
        """Async token bucket should allow bursts up to capacity."""
        limiter = AsyncTokenBucketLimiter(rate=1.0, capacity=10.0)
        with Server.basic_response_server(requests_to_handle=5) as (host, port):
            async with niquests.AsyncSession(hooks=limiter, headers={"Connection": "close"}) as session:
                start = time.monotonic()
                for _ in range(5):
                    response = await session.get(f"http://{host}:{port}")
                    assert response.status_code == 200
                elapsed = time.monotonic() - start

                # Burst should be fast - with rate=1.0 and no burst, 5 requests
                # would take 4+ seconds. With burst capacity, it should be much faster.
                # Allow 5 seconds for network overhead.
                assert elapsed < 5.0


class TestLimiterWithCustomHooks:
    """Tests for combining limiters with other hooks."""

    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=10.0), id="token_bucket"),
        ],
    )
    def test_sync_limiter_with_custom_hook(self, limiter_factory):
        """Rate limiter should work alongside custom hooks."""
        limiter = limiter_factory()
        request_count = {"value": 0}

        def count_requests(response, **_kwargs):
            request_count["value"] += 1
            return response

        with Server.basic_response_server(requests_to_handle=3) as (host, port):
            with niquests.Session(hooks=limiter, headers={"Connection": "close"}) as session:
                session.hooks["response"].append(count_requests)
                for _ in range(3):
                    session.get(f"http://{host}:{port}")

        assert request_count["value"] == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=10.0), id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=10.0), id="token_bucket"),
        ],
    )
    async def test_async_limiter_with_custom_hook(self, limiter_factory):
        """Async rate limiter should work alongside custom hooks."""
        limiter = limiter_factory()
        request_count = {"value": 0}

        async def count_requests(response, **_kwargs):
            request_count["value"] += 1
            return response

        with Server.basic_response_server(requests_to_handle=3) as (host, port):
            async with niquests.AsyncSession(hooks=limiter, headers={"Connection": "close"}) as session:
                session.hooks["response"].append(count_requests)
                for _ in range(3):
                    await session.get(f"http://{host}:{port}")

        assert request_count["value"] == 3
