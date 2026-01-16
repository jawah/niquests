from __future__ import annotations

import asyncio
import json
import typing

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from niquests import AsyncSession, RetryConfiguration, Session

app = FastAPI()


@app.get("/hello")
async def hello(request: Request):
    return {
        "method": request.method,
        "path": request.url.path,
        "query": str(request.query_params),
        "param": str(request.path_params),
        "message": "hello from asgi",
    }


@app.get("/retries")
async def retries(request: Request):
    # Use a simple counter stored in app state
    if not hasattr(app.state, "_retry_count"):
        app.state._retry_count = 0

    app.state._retry_count += 1

    if app.state._retry_count == 1:
        return JSONResponse({"message": "temporary failure"}, status_code=503)

    # Reset for next test
    count = app.state._retry_count
    app.state._retry_count = 0
    return {"message": "success", "attempts": count}


@app.api_route("/echo", methods=["GET", "POST", "PUT", "DELETE"])
async def echo(request: Request):
    body = await request.json() if request.headers.get("content-type") == "application/json" else await request.body()

    return {
        "method": request.method,
        "path": request.url.path,
        "query": str(request.query_params),
        "param": str(request.path_params),
        "body": body,
        "headers": dict(request.headers),
    }


@pytest.mark.asyncio
async def test_asgi_basic():
    async with AsyncSession(app=app) as s:
        resp = await s.get("/hello", params={"foo": "bar", "channels": [0, 3]})
        assert resp.status_code == 200
        assert resp.json()["path"] == "/hello"
        assert resp.json()["query"] == "foo=bar&channels=0&channels=3"


@pytest.mark.asyncio
async def test_asgi_retries():
    # Reset counter for test isolation
    app.state._retry_count = 0

    async with AsyncSession(app=app, retries=RetryConfiguration(total=1, status_forcelist=(503,))) as s:
        resp = await s.get("/retries")
        assert resp.status_code == 200

        resp = await s.get("/retries")
        assert resp.status_code == 200

    async with AsyncSession(app=app) as s:
        resp = await s.get("/retries")
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_asgi_aiter():
    async def fake_aiter() -> typing.AsyncIterator[bytes]:
        for _ in range(32):
            yield b"foobar"
            await asyncio.sleep(0)

    async with AsyncSession(app=app) as s:
        resp = await s.post("/echo", data=fake_aiter())
        assert resp.status_code == 200
        assert resp.json()["path"] == "/echo"
        assert resp.json()["body"] == "foobar" * 32


@pytest.mark.asyncio
async def test_asgi_stream_response():
    async with AsyncSession(app=app) as s:
        resp = await s.post(
            "/echo",
            data=b"foobar" * 32,
            stream=True,
        )
        assert resp.status_code == 200

        body = b""

        async for chunk in await resp.iter_content(6):
            body += chunk

        payload = json.loads(body)

        assert payload["path"] == "/echo"


def test_thread_asgi_basic():
    with Session(app=app) as s:
        resp = s.get("/hello", params={"foo": "bar", "channels": [0, 3]})
        assert resp.status_code == 200
        assert resp.json()["path"] == "/hello"
        assert resp.json()["query"] == "foo=bar&channels=0&channels=3"


def test_thread_asgi_retries():
    # Reset counter for test isolation
    app.state._retry_count = 0

    with Session(app=app, retries=RetryConfiguration(total=1, status_forcelist=(503,))) as s:
        resp = s.get("/retries")
        assert resp.status_code == 200

        resp = s.get("/retries")
        assert resp.status_code == 200

    with Session(app=app) as s:
        resp = s.get("/retries")
        assert resp.status_code == 503


def test_thread_asgi_stream_response():
    with Session(app=app) as s:
        with pytest.raises(ValueError):
            s.post(
                "/echo",
                data=b"foobar" * 32,
                stream=True,
            )
