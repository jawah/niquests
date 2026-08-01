from __future__ import annotations

import niquests
from niquests.adapters import HTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities

RESOLVER = "in-memory://default?hosts=httpbin.local:127.0.0.1"


def test_preview1_heuristic_and_request():
    assert capabilities.HAS_WASI_P1_SOCKETS
    assert not capabilities.HAS_WASI_P2_SOCKETS
    assert not capabilities.HAS_WASI_P2_HTTP
    assert not capabilities.HAS_WASI_TLS_SUPPORT
    with niquests.Session(resolver=RESOLVER) as session:
        assert isinstance(session.get_adapter("http://httpbin.local:8888"), HTTPAdapter)
        assert session.get("http://httpbin.local:8888/get").status_code == 200
