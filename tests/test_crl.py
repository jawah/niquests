from __future__ import annotations

from unittest.mock import patch

import pytest

from niquests import AsyncSession, ConnectionError, Session, Timeout

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

    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            "https://revoked-rsa-ev.ssl.com/",
        ],
    )
    def test_sync_revoked_certificate(self, revoked_peer_url: str) -> None:
        """This test may fail at any moment. Using several known revoked certs as targets tester."""

        with patch("niquests.sessions.is_ocsp_capable", return_value=False):
            with Session() as s:
                assert s._ocsp_cache is None
                assert s._crl_cache is None

                with pytest.raises(
                    ConnectionError,
                    match=f"Unable to establish a secure connection to {revoked_peer_url} "
                    "because the certificate has been revoked",
                ):
                    try:
                        s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                    except Timeout:
                        pytest.mark.skip(f"remote {revoked_peer_url} is unavailable at the moment...")

                assert s._crl_cache is not None
                assert s._ocsp_cache is None

                assert hasattr(s._crl_cache, "_store")
                assert isinstance(s._crl_cache._store, dict)
                assert len(s._crl_cache._store) == 1

    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            "https://revoked-rsa-ev.ssl.com/",
        ],
    )
    @pytest.mark.asyncio
    async def test_async_revoked_certificate(self, revoked_peer_url: str) -> None:
        """This test may fail at any moment. Using several known revoked certs as targets tester."""

        with patch("niquests.async_session.is_ocsp_capable", return_value=False):
            async with AsyncSession() as s:
                assert s._ocsp_cache is None
                assert s._crl_cache is None

                with pytest.raises(
                    ConnectionError,
                    match=f"Unable to establish a secure connection to {revoked_peer_url} "
                    "because the certificate has been revoked",
                ):
                    try:
                        await s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                    except Timeout:
                        pytest.mark.skip(f"remote {revoked_peer_url} is unavailable at the moment...")

                assert s._crl_cache is not None
                assert s._ocsp_cache is None

                assert hasattr(s._crl_cache, "_store")
                assert isinstance(s._crl_cache._store, dict)
                assert len(s._crl_cache._store) == 1
