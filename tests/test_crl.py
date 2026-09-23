from __future__ import annotations

import pytest

from niquests import AsyncSession, ConnectionError, Session
from niquests.extensions.revocation import RevocationConfiguration

from .revocation import CRL_URL, DIRECTORY

ROOT_CA = str(DIRECTORY / "root.pem")


@pytest.mark.usefixtures("requires_revocation_stack")
class TestCertificateRevocationList:
    def test_sync_valid_ensure_cached(self, traefik_resolver, revocation_requests) -> None:
        with Session(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            timeout=5,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            url = "https://good-crl.httpbin.local:4443/get"
            for _ in range(2):
                response = session.get(url)
                assert response.status_code == 200
                assert response.ocsp_verified is True
            assert revocation_requests.count(CRL_URL) == 1
            assert session._ocsp_cache is None
            assert len(session._crl_cache) == 1

    @pytest.mark.asyncio
    async def test_async_valid_ensure_cached(self, traefik_resolver, revocation_requests) -> None:
        async with AsyncSession(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            timeout=5,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            url = "https://good-crl.httpbin.local:4443/get"
            for _ in range(2):
                response = await session.get(url)
                assert response.status_code == 200
                assert response.ocsp_verified is True
            assert revocation_requests.count(CRL_URL) == 1
            assert session._ocsp_cache is None
            assert len(session._crl_cache) == 1

    def test_sync_revoked_certificate(self, traefik_resolver, revocation_requests) -> None:
        with Session(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            timeout=5,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            for _ in range(2):
                with pytest.raises(ConnectionError, match=r"certificate has been revoked by issuer \(cessation_of_operation\)"):
                    session.get("https://revoked-crl.httpbin.local:4443/get")
            assert revocation_requests.count(CRL_URL) == 1
            assert session._ocsp_cache is None
            assert len(session._crl_cache) == 1

    @pytest.mark.asyncio
    async def test_async_revoked_certificate(self, traefik_resolver, revocation_requests) -> None:
        async with AsyncSession(
            resolver=traefik_resolver,
            verify=ROOT_CA,
            timeout=5,
            revocation_configuration=RevocationConfiguration(strict_mode=True),
        ) as session:
            for _ in range(2):
                with pytest.raises(ConnectionError, match=r"certificate has been revoked by issuer \(cessation_of_operation\)"):
                    await session.get("https://revoked-crl.httpbin.local:4443/get")
            assert revocation_requests.count(CRL_URL) == 1
            assert session._ocsp_cache is None
            assert len(session._crl_cache) == 1
