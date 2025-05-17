from __future__ import annotations

import pytest

from niquests import AsyncSession, Session
from niquests.exceptions import ConnectionError, Timeout

try:
    import qh3
except ImportError:
    qh3 = None

OCSP_MAX_DELAY_WAIT = 5


@pytest.mark.usefixtures("requires_wan")
@pytest.mark.skipif(qh3 is None, reason="qh3 unavailable")
class TestOnlineCertificateRevocationProtocol:
    """This test class hold the minimal amount of confidence
    we need to ensure revoked certificate are properly rejected.
    Unfortunately, we need to fetch external resources through a valid WAN
    link. We may assemble a complex mocking scenario later on."""

    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            # "https://revoked.badssl.com/",
            # "https://revoked-ecc-dv.ssl.com/",
            # "https://aaacertificateservices.comodoca.com:444/",
            "https://revoked-rsa-ev.ssl.com/",
        ],
    )
    def test_sync_revoked_certificate(self, revoked_peer_url: str) -> None:
        """This test may fail at any moment. Using several known revoked certs as targets tester."""

        with Session() as s:
            assert s._ocsp_cache is None
            with pytest.raises(
                ConnectionError,
                match=f"Unable to establish a secure connection to {revoked_peer_url} because the certificate has been revoked",
            ):
                try:
                    s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                except Timeout:
                    pytest.mark.skip(f"remote {revoked_peer_url} is unavailable at the moment...")
            assert s._ocsp_cache is not None
            assert hasattr(s._ocsp_cache, "_store")
            assert isinstance(s._ocsp_cache._store, dict)
            assert len(s._ocsp_cache._store) == 1

    def test_sync_valid_ensure_cached(self) -> None:
        with Session() as s:
            assert s._ocsp_cache is None
            s.get("https://raw.githubusercontent.com/jawah/niquests/refs/heads/main/README.md", timeout=OCSP_MAX_DELAY_WAIT)
            assert s._ocsp_cache is not None
            assert hasattr(s._ocsp_cache, "_store")
            assert isinstance(s._ocsp_cache._store, dict)
            assert len(s._ocsp_cache._store) == 1
            s.get("https://pypi.org/pypi/niquests/json", timeout=OCSP_MAX_DELAY_WAIT)
            assert len(s._ocsp_cache._store) == 2
            s.get("https://one.one.one.one", timeout=OCSP_MAX_DELAY_WAIT)
            assert len(s._ocsp_cache._store) == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            # "https://revoked.badssl.com/",
            # "https://revoked-ecc-dv.ssl.com/",
            # "https://aaacertificateservices.comodoca.com:444/",
            "https://revoked-rsa-ev.ssl.com/",
        ],
    )
    async def test_async_revoked_certificate(self, revoked_peer_url: str) -> None:
        async with AsyncSession() as s:
            assert s._ocsp_cache is None
            with pytest.raises(
                ConnectionError,
                match=f"Unable to establish a secure connection to {revoked_peer_url} because the certificate has been revoked",
            ):
                try:
                    await s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                except Timeout:
                    pytest.mark.skip(f"remote {revoked_peer_url} is unavailable at the moment...")
            assert s._ocsp_cache is not None
            assert hasattr(s._ocsp_cache, "_store")
            assert isinstance(s._ocsp_cache._store, dict)
            assert len(s._ocsp_cache._store) == 1

    @pytest.mark.asyncio
    async def test_async_valid_ensure_cached(self) -> None:
        async with AsyncSession() as s:
            assert s._ocsp_cache is None
            await s.get(
                "https://raw.githubusercontent.com/jawah/niquests/refs/heads/main/README.md", timeout=OCSP_MAX_DELAY_WAIT
            )
            assert s._ocsp_cache is not None
            assert hasattr(s._ocsp_cache, "_store")
            assert isinstance(s._ocsp_cache._store, dict)
            assert len(s._ocsp_cache._store) == 1
            await s.get("https://pypi.org/pypi/niquests/json", timeout=OCSP_MAX_DELAY_WAIT)
            assert len(s._ocsp_cache._store) == 2
            await s.get("https://one.one.one.one/", timeout=OCSP_MAX_DELAY_WAIT)
            assert len(s._ocsp_cache._store) == 3
