from __future__ import annotations

import json
import time

import pytest
from niquests.packages.urllib3.exceptions import MaxRetryError

import niquests
from niquests.exceptions import InvalidSchema, SSLError


def test_buffered_get():
    response = niquests.get("https://httpbingo.org/get")
    response.raise_for_status()
    assert response.json()["url"] == "https://httpbingo.org/get"


def test_streamed_get_and_close_before_eof():
    response = niquests.get("https://httpbingo.org/stream/5", stream=True)
    first = next(response.iter_lines())
    assert json.loads(first)["url"] == "https://httpbingo.org/stream/5"
    response.close()
    assert response.raw.closed


def test_incomplete_response_body():
    with pytest.raises(Exception):
        niquests.get("https://httpbingo.org/response-headers?Content-Length=1000").content


def test_gzip_raw_and_decoded():
    encoded = niquests.get("https://httpbingo.org/gzip", stream=True)
    assert encoded.headers["content-encoding"] == "gzip"
    assert b"".join(encoded.iter_raw()).startswith(b"\x1f\x8b")

    assert niquests.get("https://httpbingo.org/gzip").json()["gzipped"] is True


def test_retry_configuration():
    retry = niquests.RetryConfiguration(total=1, status=1, status_forcelist={500}, raise_on_status=False)
    with niquests.Session(retries=retry) as session:
        assert session.get("https://httpbingo.org/status/500").status_code == 500


def test_retry_exhaustion():
    retry = niquests.RetryConfiguration(total=0, status=0, status_forcelist={500}, raise_on_status=True)
    with niquests.Session(retries=retry) as session:
        with pytest.raises(MaxRetryError):
            session.get("https://httpbingo.org/status/500")


def test_redirect_chain_and_disabled_following():
    response = niquests.get("https://httpbingo.org/redirect/3")
    assert response.url.endswith("/get")
    assert len(response.history) == 3
    assert all(item.status_code == 302 for item in response.history)

    response = niquests.get("https://httpbingo.org/redirect/3", allow_redirects=False)
    assert response.status_code == 302
    assert response.history == []
    assert response.headers["location"]


def test_307_preserves_method_and_body():
    response = niquests.post(
        "https://httpbingo.org/redirect-to?url=%2Fanything&status_code=307",
        data="payload",
        headers={"Content-Type": "text/plain"},
    )
    payload = response.json()
    assert payload["method"] == "POST"
    assert payload["data"] == "payload"
    assert len(response.history) == 1
    assert response.history[0].status_code == 307


def test_cookies_are_guest_managed():
    with niquests.Session() as session:
        response = session.get("https://httpbingo.org/cookies/set?hello=world")
        assert response.json()["cookies"]["hello"] == "world"


def test_streamed_upload_and_progress():
    pulses = []

    def chunks():
        yield "pay"
        yield b"load"

    response = niquests.post(
        "https://httpbingo.org/post",
        data=chunks(),
        headers={"Content-Type": "text/plain"},
        hooks={"on_upload": [lambda request: pulses.append(request.upload_progress)]},
    )
    assert response.json()["data"] == "payload"
    assert pulses[-1].is_completed
    assert len(pulses) >= 3


def test_upload_failure_callback():
    pulses = []

    def broken_upload():
        yield b"partial"
        raise ValueError("upload failed")

    with pytest.raises((ValueError, MaxRetryError)):
        niquests.post(
            "https://httpbingo.org/post",
            data=broken_upload(),
            hooks={"on_upload": [lambda request: pulses.append(request.upload_progress)]},
        )
    assert pulses[-1].any_error


def test_early_response_during_upload():
    early = []

    def slow_upload():
        for _ in range(128):
            yield b"x" * 4096
            time.sleep(0.01)

    response = niquests.post(
        "https://httpbingo.org/status/413",
        data=slow_upload(),
        hooks={"early_response": [lambda item: early.append(item)]},
    )
    assert response.status_code == 413
    assert not early or early[0] is response


def test_sse():
    response = niquests.get("sse://httpbingo.org/sse")
    event = response.extension.next_payload()
    assert event.event == "ping"
    assert json.loads(event.data)["id"] == 0
    response.extension.close()
    assert response.raw.closed
    assert response.raw._fp._stream is None


def test_sse_edge_formatting():
    payload = (
        "OiBjb21tZW50DQoNCnJldHJ5OiBub3BlDQoNCmV2ZW50OiBjdXN0b20NCmlkOiA3DQpyZXRyeTog"
        "MTUwMA0KZGF0YTogZmlyc3QNCmRhdGE6IHNlY29uZA0KDQpkYXRhOiBmaW5hbA=="
    )
    response = niquests.get(f"sse://httpbingo.org/base64/{payload}?content-type=text%2Fevent-stream")
    event = response.extension.next_payload()
    assert event.event == "custom"
    assert event.id == "7"
    assert event.retry == 1500
    assert event.data == "first\nsecond"
    assert response.extension.next_payload() is None


def test_websocket_is_rejected():
    with pytest.raises(InvalidSchema, match="WebSocket is unavailable through WASI HTTP"):
        niquests.get("wss://httpbingo.org/websocket/echo")


@pytest.mark.parametrize("kwargs", [{"verify": False}, {"cert": "cert.pem"}])
def test_unsupported_tls_controls(kwargs):
    with pytest.raises(SSLError):
        niquests.get("https://httpbingo.org/get", **kwargs)
