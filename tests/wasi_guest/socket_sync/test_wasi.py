from __future__ import annotations

import niquests
from niquests.adapters import HTTPAdapter
from niquests.extensions.wasi import _capabilities as capabilities

HTTPS_URL = "https://httpbin.local:4443"
ROOT_CA = "/workspace/rootCA.pem"
RESOLVER = "in-memory://default?hosts=httpbin.local:127.0.0.1"


def test_capabilities_and_adapter_selection():
    assert capabilities.HAS_WASI_P2_SOCKETS
    assert not capabilities.HAS_WASI_P1_SOCKETS
    assert not capabilities.HAS_WASI_P2_HTTP
    assert capabilities.HAS_WASI_TLS_SUPPORT
    assert isinstance(niquests.Session(resolver=RESOLVER).get_adapter(HTTPS_URL), HTTPAdapter)


def test_https_http2_and_pooling_path():
    with niquests.Session(resolver=RESOLVER, verify=ROOT_CA) as session:
        first = session.get(f"{HTTPS_URL}/get")
        second = session.get(f"{HTTPS_URL}/get")
    assert first.status_code == second.status_code == 200
    assert first.raw.version == second.raw.version == 20


def test_real_http2_trailers():
    with niquests.Session(resolver=RESOLVER, verify=ROOT_CA) as session:
        response = session.get(f"{HTTPS_URL}/trailers?trailer1=value1&trailer2=value2")
        assert response.trailers == {"trailer1": "value1", "trailer2": "value2"}


def test_redirect_chain_and_disabled_following():
    with niquests.Session(resolver=RESOLVER, verify=ROOT_CA) as session:
        response = session.get(f"{HTTPS_URL}/redirect/3")
        assert response.url.endswith("/get")
        assert len(response.history) == 3
        assert all(item.status_code == 302 for item in response.history)

        response = session.get(f"{HTTPS_URL}/redirect/3", allow_redirects=False)
        assert response.status_code == 302
        assert response.history == []
