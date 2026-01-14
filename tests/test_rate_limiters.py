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


class TestSyncLimitersUnit:
    """Unit tests for sync rate limiters without network calls."""

    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=100.0), id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=100.0, capacity=20.0), id="token_bucket"),
        ],
    )
    def test_concurrent_calls_are_serialized(self, limiter_factory):
        """Concurrent calls should be properly serialized by the lock."""
        limiter = limiter_factory()
        call_count = 0

        def make_call():
            nonlocal call_count
            limiter.pre_request(None)
            call_count += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_call) for _ in range(10)]
            concurrent.futures.wait(futures)

        assert call_count == 10

    @pytest.mark.parametrize(
        "limiter_factory,expected_delay",
        [
            pytest.param(partial(LeakyBucketLimiter, rate=10.0), 0.1, id="leaky_bucket"),
            pytest.param(partial(TokenBucketLimiter, rate=10.0, capacity=1.0), 0.1, id="token_bucket"),
        ],
    )
    def test_rate_limiting_introduces_delay(self, limiter_factory, expected_delay):
        """Rate limiting should introduce delays when limit is exceeded."""
        limiter = limiter_factory()

        # First request - immediate
        limiter.pre_request(None)

        # Second request should be delayed
        start = time.monotonic()
        limiter.pre_request(None)
        elapsed = time.monotonic() - start

        # Should have waited approximately expected_delay (with tolerance)
        assert elapsed >= expected_delay * 0.7

    def test_token_bucket_burst_no_wait(self):
        """Token bucket burst requests within capacity should not wait."""
        limiter = TokenBucketLimiter(rate=1.0, capacity=10.0)

        start = time.monotonic()
        for _ in range(5):
            limiter.pre_request(None)
        elapsed = time.monotonic() - start

        # All 5 should complete almost instantly since we have 10 tokens
        assert elapsed < 0.1

    def test_token_bucket_tokens_capped_at_capacity(self):
        """Token bucket tokens should not exceed capacity."""
        limiter = TokenBucketLimiter(rate=100.0, capacity=5.0)

        time.sleep(0.1)
        with limiter._lock:
            limiter._acquire_token()

        assert limiter.tokens <= limiter.capacity


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


class TestAsyncLimitersUnit:
    """Unit tests for async rate limiters without network calls."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=100.0), id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=100.0, capacity=20.0), id="token_bucket"),
        ],
    )
    async def test_concurrent_calls_are_serialized(self, limiter_factory):
        """Concurrent calls should be properly serialized by the lock."""
        limiter = limiter_factory()
        call_count = 0

        async def make_call():
            nonlocal call_count
            await limiter.pre_request(None)
            call_count += 1

        await asyncio.gather(*[make_call() for _ in range(10)])
        assert call_count == 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limiter_factory,expected_delay",
        [
            pytest.param(partial(AsyncLeakyBucketLimiter, rate=10.0), 0.1, id="leaky_bucket"),
            pytest.param(partial(AsyncTokenBucketLimiter, rate=10.0, capacity=1.0), 0.1, id="token_bucket"),
        ],
    )
    async def test_rate_limiting_introduces_delay(self, limiter_factory, expected_delay):
        """Rate limiting should introduce delays when limit is exceeded."""
        limiter = limiter_factory()

        # First request - immediate
        await limiter.pre_request(None)

        # Second request should be delayed
        start = time.monotonic()
        await limiter.pre_request(None)
        elapsed = time.monotonic() - start

        # Should have waited approximately expected_delay (with tolerance)
        assert elapsed >= expected_delay * 0.7

    @pytest.mark.asyncio
    async def test_token_bucket_burst_no_wait(self):
        """Token bucket burst requests within capacity should not wait."""
        limiter = AsyncTokenBucketLimiter(rate=1.0, capacity=10.0)

        start = time.monotonic()
        for _ in range(5):
            await limiter.pre_request(None)
        elapsed = time.monotonic() - start

        # All 5 should complete almost instantly since we have 10 tokens
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_token_bucket_tokens_capped_at_capacity(self):
        """Token bucket tokens should not exceed capacity."""
        limiter = AsyncTokenBucketLimiter(rate=100.0, capacity=5.0)

        await asyncio.sleep(0.1)
        async with limiter._lock:
            limiter._acquire_token()

        assert limiter.tokens <= limiter.capacity
