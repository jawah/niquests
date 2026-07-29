from __future__ import annotations

import niquests
from niquests.adapters import HTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities


def test_preview1_heuristic_and_request():
    assert capabilities.HAS_WASI_P1_SOCKETS
    assert not capabilities.HAS_WASI_P2_SOCKETS
    assert not capabilities.HAS_WASI_P2_HTTP
    assert not capabilities.HAS_WASI_TLS_SUPPORT
    with niquests.Session() as session:
        assert isinstance(session.get_adapter("http://httpbingo.org"), HTTPAdapter)
        assert session.get("http://httpbingo.org/get").status_code == 200
