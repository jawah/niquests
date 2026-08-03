from __future__ import annotations

import json
import os

import pytest
from edge_cases import run_async_edges
from niquests.packages.urllib3.exceptions import MaxRetryError

import niquests
from niquests.exceptions import InvalidSchema, ReadTimeout, SSLError


def _httpbin_target():
    target = os.environ.get("NIQUESTS_WASI_HTTP_TARGET")
    if target == "local":
        return "http://localhost:8888", "ws://localhost:8888", "psse://localhost:8888"
    if target == "live":
        return "https://httpbingo.org", "wss://httpbingo.org", "sse://httpbingo.org"
    raise RuntimeError(f"unknown NIQUESTS_WASI_HTTP_TARGET: {target!r}")


async def test_buffered_get() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{http_origin}/get")
        assert response.status_code == 200
        assert response.json()["url"] == f"{http_origin}/get"


async def test_request_options_timeout() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession(retries=0) as session:
        with pytest.raises(MaxRetryError) as exc_info:
            await session.get(f"{http_origin}/delay/2", timeout=(10, 0.05))
        assert isinstance(exc_info.value.reason, ReadTimeout)


async def test_streamed_get_and_close_before_eof() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{http_origin}/stream/5", stream=True)
        lines = response.iter_lines()
        first = await lines.__anext__()
        assert json.loads(first)["url"] == f"{http_origin}/stream/5"
        await response.close()
        assert response.raw.closed


async def test_incomplete_response_body() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        with pytest.raises(Exception):
            await session.get(f"{http_origin}/response-headers?Content-Length=1000")


async def test_gzip_raw_and_decoded() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        encoded = await session.get(f"{http_origin}/gzip", stream=True)
        raw_body = b"".join([chunk async for chunk in await encoded.iter_raw()])
        assert encoded.headers["content-encoding"] == "gzip"
        assert raw_body.startswith(b"\x1f\x8b")

        decoded = await session.get(f"{http_origin}/gzip")
        assert decoded.json()["gzipped"] is True


async def test_retry_configuration() -> None:
    http_origin, _, _ = _httpbin_target()
    retry = niquests.RetryConfiguration(total=1, status=1, status_forcelist={500}, raise_on_status=False)
    async with niquests.AsyncSession(retries=retry) as session:
        assert (await session.get(f"{http_origin}/status/500")).status_code == 500


async def test_retry_exhaustion() -> None:
    http_origin, _, _ = _httpbin_target()
    retry = niquests.RetryConfiguration(total=0, status=0, status_forcelist={500}, raise_on_status=True)
    async with niquests.AsyncSession(retries=retry) as session:
        with pytest.raises(MaxRetryError):
            await session.get(f"{http_origin}/status/500")


async def test_redirect_chain_and_disabled_following() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{http_origin}/redirect/3")
        assert response.url.endswith("/get")
        assert len(response.history) == 3
        assert all(item.status_code == 302 for item in response.history)

        response = await session.get(f"{http_origin}/redirect/3", allow_redirects=False)
        assert response.status_code == 302
        assert not response.history
        assert response.headers["location"]


async def test_307_preserves_method_and_body() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.post(
            f"{http_origin}/redirect-to?url=%2Fanything&status_code=307",
            data="payload",
            headers={"Content-Type": "text/plain"},
        )
        payload = response.json()
        assert payload["method"] == "POST"
        assert payload["data"] == "payload"
        assert len(response.history) == 1
        assert response.history[0].status_code == 307


async def test_cookies_are_guest_managed() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{http_origin}/cookies/set?hello=world")
        assert response.json()["cookies"]["hello"] == "world"


async def test_streamed_upload_and_progress() -> None:
    http_origin, _, _ = _httpbin_target()
    pulses = []

    async def chunks():
        yield b"pay"
        yield b"load"

    async def record_upload(request):
        pulses.append(request.upload_progress)

    async with niquests.AsyncSession() as session:
        response = await session.post(
            f"{http_origin}/post",
            data=chunks(),
            headers={"Content-Type": "text/plain"},
            hooks={"on_upload": [record_upload]},
        )
        assert response.json()["data"] == "payload"
        assert len(pulses) >= 3
        assert pulses[-1].is_completed


async def test_upload_failure_callback() -> None:
    http_origin, _, _ = _httpbin_target()
    pulses = []

    async def broken_upload():
        yield b"partial"
        raise ValueError("upload failed")

    async def record_upload(request):
        pulses.append(request.upload_progress)

    async with niquests.AsyncSession() as session:
        await session.post(
            f"{http_origin}/post",
            data=broken_upload(),
            hooks={"on_upload": [record_upload]},
        )
    assert pulses
    assert pulses[-1].any_error


async def test_early_response_during_upload() -> None:
    http_origin, _, _ = _httpbin_target()
    early = []

    async def slow_upload():
        for _ in range(128):
            yield b"x" * 4096
            await __import__("asyncio").sleep(0.01)

    async def record_early(response):
        early.append(response)

    async with niquests.AsyncSession() as session:
        response = await session.post(
            f"{http_origin}/status/413",
            data=slow_upload(),
            hooks={"early_response": [record_early]},
        )
        assert response.status_code == 413
        assert not early or early[0] is response


async def test_sse() -> None:
    _, _, sse_origin = _httpbin_target()
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{sse_origin}/sse")
        event = await response.extension.next_payload()
        assert event.event == "ping"
        assert json.loads(event.data)["id"] == 0
        await response.extension.close()
        assert response.raw.closed
        assert response.raw._fp._reader is None


async def test_sse_edge_formatting() -> None:
    _, _, sse_origin = _httpbin_target()
    payload = (
        "OiBjb21tZW50DQoNCnJldHJ5OiBub3BlDQoNCmV2ZW50OiBjdXN0b20NCmlkOiA3DQpyZXRyeTog"
        "MTUwMA0KZGF0YTogZmlyc3QNCmRhdGE6IHNlY29uZA0KDQpkYXRhOiBmaW5hbA=="
    )
    async with niquests.AsyncSession() as session:
        response = await session.get(f"{sse_origin}/base64/{payload}?content-type=text%2Fevent-stream")
        event = await response.extension.next_payload()
        assert event.event == "custom"
        assert event.id == "7"
        assert event.retry == 1500
        assert event.data == "first\nsecond"
        assert await response.extension.next_payload() is None


async def test_websocket_is_rejected() -> None:
    _, websocket_origin, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        with pytest.raises(InvalidSchema, match="WebSocket is unavailable through WASI HTTP"):
            await session.get(f"{websocket_origin}/websocket/echo")


async def test_unsupported_tls_controls() -> None:
    http_origin, _, _ = _httpbin_target()
    async with niquests.AsyncSession() as session:
        for kwargs in ({"verify": False}, {"cert": "cert.pem"}):
            with pytest.raises(SSLError):
                await session.get(f"{http_origin}/get", **kwargs)


async def test_defensive_edges() -> None:
    assert await run_async_edges()


CASES = {
    "buffered-get": test_buffered_get,
    "request-options-timeout": test_request_options_timeout,
    "streamed-get-and-close-before-eof": test_streamed_get_and_close_before_eof,
    "incomplete-response-body": test_incomplete_response_body,
    "gzip-raw-and-decoded": test_gzip_raw_and_decoded,
    "retry-configuration": test_retry_configuration,
    "retry-exhaustion": test_retry_exhaustion,
    "redirect-chain-and-disabled-following": test_redirect_chain_and_disabled_following,
    "307-preserves-method-and-body": test_307_preserves_method_and_body,
    "cookies-are-guest-managed": test_cookies_are_guest_managed,
    "streamed-upload-and-progress": test_streamed_upload_and_progress,
    "upload-failure-callback": test_upload_failure_callback,
    "early-response-during-upload": test_early_response_during_upload,
    "sse": test_sse,
    "sse-edge-formatting": test_sse_edge_formatting,
    "websocket-is-rejected": test_websocket_is_rejected,
    "unsupported-tls-controls": test_unsupported_tls_controls,
    "defensive-edges": test_defensive_edges,
}
