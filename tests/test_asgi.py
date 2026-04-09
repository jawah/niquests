from __future__ import annotations

import asyncio
import json
import typing

import pytest
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse
from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent
from starlette.responses import StreamingResponse

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


@app.websocket("/ws-echo")
async def ws_echo(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive()
        except Exception:
            break
        if data["type"] == "websocket.disconnect":
            break
        if "text" in data:
            await websocket.send_text(f"echo: {data['text']}")
        elif "bytes" in data:
            await websocket.send_bytes(data["bytes"])


@app.get("/sse-events")
async def sse_events():
    async def generate():
        for i in range(3):
            yield f"event: message\ndata: event {i}\nid: {i}\n\n"
        yield "event: done\ndata: finished\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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


@pytest.mark.asyncio
async def test_asgi_websocket_text():
    async with AsyncSession(app=app) as s:
        resp = await s.get("wss://default/ws-echo")
        assert resp.status_code == 101

        ext = resp.extension
        assert ext is not None
        assert ext.closed is False

        await ext.send_payload("hello")
        msg = await ext.next_payload()
        assert msg == "echo: hello"

        await ext.send_payload("world")
        msg = await ext.next_payload()
        assert msg == "echo: world"

        await ext.close()
        assert ext.closed is True


@pytest.mark.asyncio
async def test_asgi_websocket_binary():
    async with AsyncSession(app=app) as s:
        resp = await s.get("wss://default/ws-echo")
        ext = resp.extension

        await ext.send_payload(b"\x00\x01\x02")
        msg = await ext.next_payload()
        assert msg == b"\x00\x01\x02"

        await ext.close()


@pytest.mark.asyncio
async def test_asgi_sse():
    async with AsyncSession(app=app) as s:
        resp = await s.get("sse://default/sse-events")
        assert resp.status_code == 200

        ext = resp.extension
        assert ext is not None
        assert ext.closed is False

        events = []
        while True:
            event = await ext.next_payload()
            if event is None:
                break
            assert isinstance(event, ServerSentEvent)
            events.append(event)

        assert len(events) == 4
        assert events[0].data == "event 0"
        assert events[0].event == "message"
        assert events[0].id == "0"
        assert events[3].event == "done"
        assert events[3].data == "finished"
        assert ext.closed is True


@pytest.mark.asyncio
async def test_asgi_sse_send_forbidden():
    async with AsyncSession(app=app) as s:
        resp = await s.get("sse://default/sse-events")
        ext = resp.extension

        with pytest.raises(NotImplementedError):
            await ext.send_payload("nope")

        await ext.close()


def test_thread_asgi_websocket_text():
    with Session(app=app) as s:
        resp = s.get("wss://default/ws-echo")
        assert resp.status_code == 101

        ext = resp.extension
        assert ext is not None
        assert ext.closed is False

        ext.send_payload("hello")
        msg = ext.next_payload()
        assert msg == "echo: hello"

        ext.send_payload("world")
        msg = ext.next_payload()
        assert msg == "echo: world"

        ext.close()
        assert ext.closed is True


def test_thread_asgi_websocket_binary():
    with Session(app=app) as s:
        resp = s.get("wss://default/ws-echo")
        ext = resp.extension

        ext.send_payload(b"\x00\x01\x02")
        msg = ext.next_payload()
        assert msg == b"\x00\x01\x02"

        ext.close()


def test_thread_asgi_sse():
    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")
        assert resp.status_code == 200

        ext = resp.extension
        assert ext is not None
        assert ext.closed is False

        events = []
        while True:
            event = ext.next_payload()
            if event is None:
                break
            assert isinstance(event, ServerSentEvent)
            events.append(event)

        assert len(events) == 4
        assert events[0].data == "event 0"
        assert events[0].event == "message"
        assert events[0].id == "0"
        assert events[3].event == "done"
        assert events[3].data == "finished"
        assert ext.closed is True


def test_thread_asgi_sse_send_forbidden():
    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")
        ext = resp.extension

        with pytest.raises(NotImplementedError):
            ext.send_payload("nope")

        ext.close()
