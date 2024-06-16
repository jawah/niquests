import pytest

from niquests import Session, AsyncSession
from niquests.exceptions import ConnectionError, Timeout

OCSP_MAX_DELAY_WAIT = 5


@pytest.mark.usefixtures("requires_wan")
class TestOnlineCertificateRevocationProtocol:
    """This test class hold the minimal amount of confidence
    we need to ensure revoked certificate are properly rejected.
    Unfortunately, we need to fetch external resources through a valid WAN
    link. We may assemble a complex mocking scenario later on."""

    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            "https://revoked.badssl.com/",
            # "https://revoked-rsa-ev.ssl.com/",
            # "https://revoked-ecc-dv.ssl.com/",
        ],
    )
    def test_sync_revoked_certificate(self, revoked_peer_url: str) -> None:
        """This test may fail at any moment. Using several known revoked certs as targets tester."""

        with Session() as s:
            with pytest.raises(
                ConnectionError,
                match=f"Unable to establish a secure connection to {revoked_peer_url} because the certificate has been revoked",
            ):
                try:
                    s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                except Timeout:
                    pytest.mark.skip(
                        f"remote {revoked_peer_url} is unavailable at the moment..."
                    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "revoked_peer_url",
        [
            "https://revoked.badssl.com/",
            # "https://revoked-rsa-ev.ssl.com/",
            # "https://revoked-ecc-dv.ssl.com/",
        ],
    )
    async def test_async_revoked_certificate(self, revoked_peer_url: str) -> None:
        async with AsyncSession() as s:
            with pytest.raises(
                ConnectionError,
                match=f"Unable to establish a secure connection to {revoked_peer_url} because the certificate has been revoked",
            ):
                try:
                    await s.get(revoked_peer_url, timeout=OCSP_MAX_DELAY_WAIT)
                except Timeout:
                    pytest.mark.skip(
                        f"remote {revoked_peer_url} is unavailable at the moment..."
                    )
