from __future__ import annotations

import pytest

from niquests import AsyncSession, Session

try:
    import qh3
except ImportError:
    qh3 = None

OCSP_MAX_DELAY_WAIT = 5


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.skipif(qh3 is None, reason="qh3 unavailable")
class TestCertificateRevocationList:
    """This test class hold the minimal amount of confidence
    we need to ensure that we are fetching CRLs appropriately and parsing/validating them."""

    def test_sync_valid_ensure_cached(self) -> None:
        with Session() as s:
            assert s._ocsp_cache is None
            assert s._crl_cache is None
            s.get("https://httpbingo.org/get", timeout=OCSP_MAX_DELAY_WAIT)
            assert s._ocsp_cache is None
            assert s._crl_cache is not None
            assert hasattr(s._crl_cache, "_store")
            assert isinstance(s._crl_cache._store, dict)
            assert len(s._crl_cache._store) == 1

            s.get("https://httpbingo.org/headers", timeout=OCSP_MAX_DELAY_WAIT)
            assert s._crl_cache is not None
            assert hasattr(s._crl_cache, "_store")
            assert isinstance(s._crl_cache._store, dict)
            assert len(s._crl_cache._store) == 1

    @pytest.mark.asyncio
    async def test_async_valid_ensure_cached(self) -> None:
        async with AsyncSession() as s:
            assert s._ocsp_cache is None
            assert s._crl_cache is None
            await s.get("https://httpbingo.org/get", timeout=OCSP_MAX_DELAY_WAIT)
            assert s._ocsp_cache is None
            assert s._crl_cache is not None
            assert hasattr(s._crl_cache, "_store")
            assert isinstance(s._crl_cache._store, dict)
            assert len(s._crl_cache._store) == 1
