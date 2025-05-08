from __future__ import annotations

import pytest
from niquests import PreparedRequest, Response
from niquests.middlewares import Middleware, MiddlewareExecutor, AsyncMiddlewareExecutor
from inspect import iscoroutinefunction


# Mock Middleware classes for testing
class SyncMiddleware(Middleware):
    def __init__(self):
        self.request_called = False
        self.response_called = False
        self.request_kwargs = {}
        self.response_kwargs = {}

    def on_request(self, request: PreparedRequest, *args, **kwargs) -> None:
        self.request_called = True
        self.request_kwargs = kwargs
        if hasattr(request, "test_data"):
            request.test_data += "_request"

    def on_response(self, response: Response, *args, **kwargs) -> None:
        self.response_called = True
        self.response_kwargs = kwargs
        if hasattr(response, "test_data"):
            response.test_data += "_response"


class AsyncMiddleware(Middleware):
    def __init__(self):
        self.request_called = False
        self.response_called = False
        self.request_kwargs = {}
        self.response_kwargs = {}

    async def on_request(self, request: PreparedRequest, *args, **kwargs) -> None:
        self.request_called = True
        self.request_kwargs = kwargs
        if hasattr(request, "test_data"):
            request.test_data += "_async_request"

    async def on_response(self, response: Response, *args, **kwargs) -> None:
        self.response_called = True
        self.response_kwargs = kwargs
        if hasattr(response, "test_data"):
            response.test_data += "_async_response"


# Test fixtures
@pytest.fixture
def prepared_request():
    request = PreparedRequest()
    request.test_data = "initial"
    return request


@pytest.fixture
def response():
    response = Response()
    response.test_data = "initial"
    return response


@pytest.fixture
def sync_middleware():
    return SyncMiddleware()


@pytest.fixture
def async_middleware():
    return AsyncMiddleware()


# Synchronous MiddlewareExecutor Tests
def test_execute_on_request_sync(prepared_request, sync_middleware):
    executor = MiddlewareExecutor([sync_middleware])
    executor.on_request(prepared_request, extra="test")

    assert sync_middleware.request_called
    assert sync_middleware.request_kwargs == {"extra": "test"}
    assert prepared_request.test_data == "initial_request"


def test_execute_on_response_sync(response, sync_middleware):
    executor = MiddlewareExecutor([sync_middleware])
    executor.on_response(response, extra="test")

    assert sync_middleware.response_called
    assert sync_middleware.response_kwargs == {"extra": "test"}
    assert response.test_data == "initial_response"


def test_multiple_sync_middlewares(prepared_request, response):
    middleware1 = SyncMiddleware()
    middleware2 = SyncMiddleware()
    executor = MiddlewareExecutor([middleware1, middleware2])

    executor.on_request(prepared_request)
    assert prepared_request.test_data == "initial_request_request"

    executor.on_response(response)
    assert response.test_data == "initial_response_response"


def test_sync_executor_call_method(prepared_request, response, sync_middleware):
    executor = MiddlewareExecutor([sync_middleware])

    executor("on_request", request=prepared_request, extra="test")
    assert sync_middleware.request_called
    assert sync_middleware.request_kwargs == {"extra": "test"}
    assert prepared_request.test_data == "initial_request"

    executor("on_response", response=response, extra="test")
    assert sync_middleware.response_called
    assert sync_middleware.response_kwargs == {"extra": "test"}
    assert response.test_data == "initial_response"


# Asynchronous MiddlewareExecutor Tests
@pytest.mark.asyncio
async def test_execute_on_request_async(prepared_request, async_middleware):
    executor = AsyncMiddlewareExecutor([async_middleware])
    await executor.on_request(prepared_request, extra="test")

    assert async_middleware.request_called
    assert async_middleware.request_kwargs == {"extra": "test"}
    assert prepared_request.test_data == "initial_async_request"


@pytest.mark.asyncio
async def test_execute_on_response_async(response, async_middleware):
    executor = AsyncMiddlewareExecutor([async_middleware])
    await executor.on_response(response, extra="test")

    assert async_middleware.response_called
    assert async_middleware.response_kwargs == {"extra": "test"}
    assert response.test_data == "initial_async_response"


@pytest.mark.asyncio
async def test_mixed_sync_async_middlewares(prepared_request, response, sync_middleware, async_middleware):
    executor = AsyncMiddlewareExecutor([sync_middleware, async_middleware])

    await executor.on_request(prepared_request)
    assert prepared_request.test_data == "initial_request_async_request"

    await executor.on_response(response)
    assert response.test_data == "initial_response_async_response"


@pytest.mark.asyncio
async def test_async_executor_with_sync_middleware(prepared_request, response, sync_middleware):
    executor = AsyncMiddlewareExecutor([sync_middleware])

    await executor.on_request(prepared_request, extra="test")
    assert sync_middleware.request_called
    assert sync_middleware.request_kwargs == {"extra": "test"}
    assert prepared_request.test_data == "initial_request"

    await executor.on_response(response, extra="test")
    assert sync_middleware.response_called
    assert sync_middleware.response_kwargs == {"extra": "test"}
    assert response.test_data == "initial_response"


@pytest.mark.asyncio
async def test_async_executor_call_method(prepared_request, response, async_middleware):
    executor = AsyncMiddlewareExecutor([async_middleware])

    await executor("on_request", request=prepared_request, extra="test")
    assert async_middleware.request_called
    assert async_middleware.request_kwargs == {"extra": "test"}
    assert prepared_request.test_data == "initial_async_request"

    await executor("on_response", response=response, extra="test")
    assert async_middleware.response_called
    assert async_middleware.response_kwargs == {"extra": "test"}
    assert response.test_data == "initial_async_response"


# Edge Case Tests
def test_empty_middleware_list_sync(prepared_request, response):
    executor = MiddlewareExecutor([])

    executor.on_request(prepared_request)
    executor.on_response(response)

    assert prepared_request.test_data == "initial"
    assert response.test_data == "initial"


@pytest.mark.asyncio
async def test_empty_middleware_list_async(prepared_request, response):
    executor = AsyncMiddlewareExecutor([])

    await executor.on_request(prepared_request)
    await executor.on_response(response)

    assert prepared_request.test_data == "initial"
    assert response.test_data == "initial"


def test_middleware_no_modification_sync(prepared_request, response):
    class NoOpMiddleware(Middleware):
        pass

    executor = MiddlewareExecutor([NoOpMiddleware()])

    executor.on_request(prepared_request)
    executor.on_response(response)

    assert prepared_request.test_data == "initial"
    assert response.test_data == "initial"


@pytest.mark.asyncio
async def test_middleware_no_modification_async(prepared_request, response):
    class NoOpMiddleware(Middleware):
        pass

    executor = AsyncMiddlewareExecutor([NoOpMiddleware()])

    await executor.on_request(prepared_request)
    await executor.on_response(response)

    assert prepared_request.test_data == "initial"
    assert response.test_data == "initial"