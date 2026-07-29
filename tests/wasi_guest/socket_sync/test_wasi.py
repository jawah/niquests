from __future__ import annotations

import niquests
from niquests.adapters import HTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities


def test_capabilities_and_adapter_selection():
    assert capabilities.HAS_WASI_P2_SOCKETS
    assert not capabilities.HAS_WASI_P1_SOCKETS
    assert not capabilities.HAS_WASI_P2_HTTP
    assert capabilities.HAS_WASI_TLS_SUPPORT
    assert isinstance(niquests.Session().get_adapter("https://httpbingo.org"), HTTPAdapter)


def test_https_http2_and_pooling_path():
    with niquests.Session() as session:
        first = session.get("https://httpbingo.org/get")
        second = session.get("https://httpbingo.org/get")
    assert first.status_code == second.status_code == 200
    assert first.raw.version == second.raw.version == 20


def test_real_http2_trailers():
    response = niquests.get("https://httpbingo.org/trailers?trailer1=value1&trailer2=value2")
    assert response.trailers == {"trailer1": "value1", "trailer2": "value2"}


def test_redirect_chain_and_disabled_following():
    response = niquests.get("https://httpbingo.org/redirect/3")
    assert response.url.endswith("/get")
    assert len(response.history) == 3
    assert all(item.status_code == 302 for item in response.history)

    response = niquests.get("https://httpbingo.org/redirect/3", allow_redirects=False)
    assert response.status_code == 302
    assert response.history == []
