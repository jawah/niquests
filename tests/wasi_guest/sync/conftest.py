from __future__ import annotations

import gc
import os

import pytest


@pytest.fixture(
    params=[
        pytest.param(
            ("http://localhost:8888", "ws://localhost:8888", "psse://localhost:8888"),
            id="local",
        ),
        pytest.param(
            ("https://httpbingo.org", "wss://httpbingo.org", "sse://httpbingo.org"),
            id="live",
        ),
    ]
)
def httpbin_target(request):
    if request.param[0].startswith("https://") and os.environ.get("NIQUESTS_WASI_WAN_AVAILABLE") != "true":
        pytest.skip("Test requires WAN access to httpbingo.org")
    return request.param


@pytest.fixture(autouse=True)
def collect_component_resources():
    yield
    gc.collect()
