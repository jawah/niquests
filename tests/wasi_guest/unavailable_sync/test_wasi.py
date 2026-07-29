from __future__ import annotations

import pytest

import niquests
from niquests.exceptions import InvalidSchema
from niquests.extensions.wasi import _capabilities as capabilities


def test_all_capabilities_are_unavailable():
    assert not capabilities.HAS_WASI_P1_SOCKETS
    assert not capabilities.HAS_WASI_P2_SOCKETS
    assert not capabilities.HAS_WASI_P2_HTTP


@pytest.mark.parametrize("url", ["http://httpbingo.org/get", "https://httpbingo.org/get"])
def test_requests_raise_actionable_error(url):
    with pytest.raises(InvalidSchema, match="No connection adapters were found"):
        niquests.get(url)


def test_http_fallback_adapter_is_not_importable():
    with pytest.raises(ImportError):
        from niquests.extensions.wasi._adapter import WASIAdapter  # noqa: F401
