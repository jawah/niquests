from __future__ import annotations

import pytest

from niquests import AsyncMiddleware, AsyncSession, Middleware, PreparedRequest, Response, Session


# Synchronous Middleware for Testing
class LoggingMiddleware(Middleware):
    def __init__(self):
        self.calls = []

    def pre_request(self, session: Session, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("pre_request", request.method, request.url))
        request.headers["X-Test"] = "pre_request"

    def pre_send(self, session: Session, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("pre_send", request.method, request.url))

    def on_upload(self, session: Session, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("on_upload", request.method, request.url))

    def early_response(self, session: Session, response: Response, *args, **kwargs) -> None:
        self.calls.append(("early_response", response.status_code))

    def response(self, session: Session, response: Response, *args, **kwargs) -> None:
        self.calls.append(("response", response.status_code))
        response.headers["X-Test-Response"] = "response"


# Asynchronous Middleware for Testing
class AsyncLoggingMiddleware(AsyncMiddleware):
    def __init__(self):
        self.calls = []

    async def pre_request(self, session: AsyncSession, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("pre_request", request.method, request.url))
        request.headers["X-Test"] = "pre_request"

    async def pre_send(self, session: AsyncSession, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("pre_send", request.method, request.url))

    async def on_upload(self, session: AsyncSession, request: PreparedRequest, *args, **kwargs) -> None:
        self.calls.append(("on_upload", request.method, request.url))

    async def early_response(self, session: AsyncSession, response: Response, *args, **kwargs) -> None:
        self.calls.append(("early_response", response.status_code))

    async def response(self, session: AsyncSession, response: Response, *args, **kwargs) -> None:
        self.calls.append(("response", response.status_code))
        response.headers["X-Test-Response"] = "response"


# Synchronous Tests
def test_middleware_session_level():
    middleware = LoggingMiddleware()
    with Session(middlewares=[middleware]) as s:
        response = s.get("https://httpbin.org/get")

    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"
    assert response.headers.get("X-Test-Response") == "response"


def test_middleware_request_level():
    middleware = LoggingMiddleware()
    with Session() as s:
        response = s.get("https://httpbin.org/get", middlewares=[middleware])

    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"
    assert response.headers.get("X-Test-Response") == "response"


def test_multiple_middlewares():
    middleware1 = LoggingMiddleware()
    middleware2 = LoggingMiddleware()
    with Session(middlewares=[middleware1]) as s:
        s.get("https://httpbin.org/get", middlewares=[middleware2])

    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware1.calls
    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware2.calls
    assert ("response", 200) in middleware1.calls
    assert ("response", 200) in middleware2.calls


def test_middleware_with_post():
    middleware = LoggingMiddleware()
    with Session(middlewares=[middleware]) as s:
        response = s.post("https://httpbin.org/post", json={"key": "value"})

    assert ("pre_request", "POST", "https://httpbin.org/post") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"


# Asynchronous Tests
@pytest.mark.asyncio
async def test_async_middleware_session_level():
    middleware = AsyncLoggingMiddleware()
    async with AsyncSession(middlewares=[middleware]) as s:
        response = await s.get("https://httpbin.org/get")

    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"
    assert response.headers.get("X-Test-Response") == "response"


@pytest.mark.asyncio
async def test_async_middleware_request_level():
    middleware = AsyncLoggingMiddleware()
    async with AsyncSession() as s:
        response = await s.get("https://httpbin.org/get", middlewares=[middleware])
    assert ("pre_request", "GET", "https://httpbin.org/get") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"
    assert response.headers.get("X-Test-Response") == "response"


@pytest.mark.asyncio
async def test_mixed_middlewares():
    sync_middleware = LoggingMiddleware()
    async_middleware = AsyncLoggingMiddleware()
    async with AsyncSession(middlewares=[sync_middleware, async_middleware]) as s:
        await s.get("https://httpbin.org/get")

    assert ("pre_request", "GET", "https://httpbin.org/get") in sync_middleware.calls
    assert ("pre_request", "GET", "https://httpbin.org/get") in async_middleware.calls
    assert ("response", 200) in sync_middleware.calls
    assert ("response", 200) in async_middleware.calls


@pytest.mark.asyncio
async def test_async_middleware_with_post():
    middleware = AsyncLoggingMiddleware()
    async with AsyncSession(middlewares=[middleware]) as s:
        response = await s.post("https://httpbin.org/post", json={"key": "value"})

    assert ("pre_request", "POST", "https://httpbin.org/post") in middleware.calls
    assert ("response", 200) in middleware.calls
    assert response.request.headers.get("X-Test") == "pre_request"
