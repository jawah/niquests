from __future__ import annotations

from pathlib import Path

import pytest

from niquests import AsyncSession, Session
from niquests.exceptions import ConnectionError
from niquests.extensions.revocation import RevocationConfiguration

try:
    import qh3
except ImportError:
    qh3 = None


ROOT_CA = str(Path(__file__).resolve().parents[1] / "traefik" / "revocation" / "root.pem")


@pytest.mark.usefixtures("requires_revocation_stack")
@pytest.mark.skipif(qh3 is None, reason="qh3 unavailable")
class TestOnlineCertificateRevocationProtocol:
    def test_sync_revoked_certificate(self, traefik_resolver) -> None:
        with Session(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            with pytest.raises(ConnectionError, match="certificate has been revoked"):
                session.get("https://revoked-ocsp.httpbin.local:4443/get", verify=ROOT_CA)
            assert len(session._ocsp_cache._store) == 1

    def test_sync_valid_ensure_cached(self, traefik_resolver) -> None:
        with Session(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            url = "https://good-ocsp.httpbin.local:4443/get"
            assert session.get(url, verify=ROOT_CA).status_code == 200
            assert session.get(url, verify=ROOT_CA).status_code == 200
            assert len(session._ocsp_cache._store) == 1

    @pytest.mark.asyncio
    async def test_async_revoked_certificate(self, traefik_resolver) -> None:
        async with AsyncSession(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            with pytest.raises(ConnectionError, match="certificate has been revoked"):
                await session.get("https://revoked-ocsp.httpbin.local:4443/get", verify=ROOT_CA)
            assert len(session._ocsp_cache._store) == 1

    @pytest.mark.asyncio
    async def test_async_valid_ensure_cached(self, traefik_resolver) -> None:
        async with AsyncSession(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            url = "https://good-ocsp.httpbin.local:4443/get"
            assert (await session.get(url, verify=ROOT_CA)).status_code == 200
            assert (await session.get(url, verify=ROOT_CA)).status_code == 200
            assert len(session._ocsp_cache._store) == 1
