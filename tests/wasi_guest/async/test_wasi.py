from __future__ import annotations

import json

import pytest
from edge_cases import run_async_edges
from niquests.packages.urllib3.exceptions import MaxRetryError

import niquests
from niquests.exceptions import InvalidSchema, ReadTimeout, SSLError


async def test_buffered_get() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.get("https://httpbingo.org/get")
        assert response.status_code == 200
        assert response.json()["url"].endswith("/get")


async def test_request_options_timeout() -> None:
    async with niquests.AsyncSession(retries=0) as session:
        with pytest.raises(MaxRetryError) as exc_info:
            await session.get("https://httpbingo.org/delay/2", timeout=(10, 0.05))
        assert isinstance(exc_info.value.reason, ReadTimeout)


async def test_streamed_get_and_close_before_eof() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.get("https://httpbingo.org/stream/5", stream=True)
        lines = response.iter_lines()
        first = await lines.__anext__()
        assert json.loads(first)["url"].endswith("/stream/5")
        await response.close()
        assert response.raw.closed


async def test_incomplete_response_body() -> None:
    async with niquests.AsyncSession() as session:
        with pytest.raises(Exception):
            await session.get("https://httpbingo.org/response-headers?Content-Length=1000")


async def test_gzip_raw_and_decoded() -> None:
    async with niquests.AsyncSession() as session:
        encoded = await session.get("https://httpbingo.org/gzip", stream=True)
        raw_body = b"".join([chunk async for chunk in await encoded.iter_raw()])
        assert encoded.headers["content-encoding"] == "gzip"
        assert raw_body.startswith(b"\x1f\x8b")

        decoded = await session.get("https://httpbingo.org/gzip")
        assert decoded.json()["gzipped"] is True


async def test_retry_configuration() -> None:
    retry = niquests.RetryConfiguration(total=1, status=1, status_forcelist={500}, raise_on_status=False)
    async with niquests.AsyncSession(retries=retry) as session:
        assert (await session.get("https://httpbingo.org/status/500")).status_code == 500


async def test_retry_exhaustion() -> None:
    retry = niquests.RetryConfiguration(total=0, status=0, status_forcelist={500}, raise_on_status=True)
    async with niquests.AsyncSession(retries=retry) as session:
        with pytest.raises(MaxRetryError):
            await session.get("https://httpbingo.org/status/500")


async def test_redirect_chain_and_disabled_following() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.get("https://httpbingo.org/redirect/3")
        assert response.url.endswith("/get")
        assert len(response.history) == 3
        assert all(item.status_code == 302 for item in response.history)

        response = await session.get("https://httpbingo.org/redirect/3", allow_redirects=False)
        assert response.status_code == 302
        assert not response.history
        assert response.headers["location"]


async def test_307_preserves_method_and_body() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.post(
            "https://httpbingo.org/redirect-to?url=%2Fanything&status_code=307",
            data="payload",
            headers={"Content-Type": "text/plain"},
        )
        payload = response.json()
        assert payload["method"] == "POST"
        assert payload["data"] == "payload"
        assert len(response.history) == 1
        assert response.history[0].status_code == 307


async def test_cookies_are_guest_managed() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.get("https://httpbingo.org/cookies/set?hello=world")
        assert response.json()["cookies"]["hello"] == "world"


async def test_streamed_upload_and_progress() -> None:
    pulses = []

    async def chunks():
        yield b"pay"
        yield b"load"

    async def record_upload(request):
        pulses.append(request.upload_progress)

    async with niquests.AsyncSession() as session:
        response = await session.post(
            "https://httpbingo.org/post",
            data=chunks(),
            headers={"Content-Type": "text/plain"},
            hooks={"on_upload": [record_upload]},
        )
        assert response.json()["data"] == "payload"
        assert len(pulses) >= 3
        assert pulses[-1].is_completed


async def test_upload_failure_callback() -> None:
    pulses = []

    async def broken_upload():
        yield b"partial"
        raise ValueError("upload failed")

    async def record_upload(request):
        pulses.append(request.upload_progress)

    async with niquests.AsyncSession() as session:
        await session.post(
            "https://httpbingo.org/post",
            data=broken_upload(),
            hooks={"on_upload": [record_upload]},
        )
    assert pulses
    assert pulses[-1].any_error


async def test_early_response_during_upload() -> None:
    early = []

    async def slow_upload():
        for _ in range(128):
            yield b"x" * 4096
            await __import__("asyncio").sleep(0.01)

    async def record_early(response):
        early.append(response)

    async with niquests.AsyncSession() as session:
        response = await session.post(
            "https://httpbingo.org/status/413",
            data=slow_upload(),
            hooks={"early_response": [record_early]},
        )
        assert response.status_code == 413
        assert not early or early[0] is response


async def test_sse() -> None:
    async with niquests.AsyncSession() as session:
        response = await session.get("sse://httpbingo.org/sse")
        event = await response.extension.next_payload()
        assert event.event == "ping"
        assert json.loads(event.data)["id"] == 0
        await response.extension.close()
        assert response.raw.closed
        assert response.raw._fp._reader is None


async def test_sse_edge_formatting() -> None:
    payload = (
        "OiBjb21tZW50DQoNCnJldHJ5OiBub3BlDQoNCmV2ZW50OiBjdXN0b20NCmlkOiA3DQpyZXRyeTog"
        "MTUwMA0KZGF0YTogZmlyc3QNCmRhdGE6IHNlY29uZA0KDQpkYXRhOiBmaW5hbA=="
    )
    async with niquests.AsyncSession() as session:
        response = await session.get(f"sse://httpbingo.org/base64/{payload}?content-type=text%2Fevent-stream")
        event = await response.extension.next_payload()
        assert event.event == "custom"
        assert event.id == "7"
        assert event.retry == 1500
        assert event.data == "first\nsecond"
        assert await response.extension.next_payload() is None


async def test_websocket_is_rejected() -> None:
    async with niquests.AsyncSession() as session:
        with pytest.raises(InvalidSchema, match="WebSocket is unavailable through WASI HTTP"):
            await session.get("wss://httpbingo.org/websocket/echo")


async def test_unsupported_tls_controls() -> None:
    async with niquests.AsyncSession() as session:
        for kwargs in ({"verify": False}, {"cert": "cert.pem"}):
            with pytest.raises(SSLError):
                await session.get("https://httpbingo.org/get", **kwargs)


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
