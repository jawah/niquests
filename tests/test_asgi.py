from __future__ import annotations

import json

import pytest
from fastapi import FastAPI, Request

from niquests import AsyncSession

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
