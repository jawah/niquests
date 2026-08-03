from __future__ import annotations

import niquests
from niquests.adapters import HTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities
from niquests.extensions.wasi._adapter import WASIAdapter


def test_hybrid_selection_and_requests():
    assert capabilities.HAS_WASI_P2_SOCKETS
    assert capabilities.HAS_WASI_P2_HTTP
    assert not capabilities.HAS_WASI_TLS_SUPPORT
    with niquests.Session() as session:
        assert isinstance(session.get_adapter("http://localhost:8888"), HTTPAdapter)
        assert isinstance(session.get_adapter("https://httpbingo.org"), WASIAdapter)
        assert session.get("http://localhost:8888/get").status_code == 200
        assert session.get("https://httpbingo.org/get").status_code == 200
