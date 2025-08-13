from __future__ import annotations

import asyncio
import datetime
import ipaddress
import ssl
import typing
import warnings
from contextlib import asynccontextmanager
from random import randint

from qh3._hazmat import (
    Certificate,
    OCSPCertStatus,
    OCSPRequest,
    OCSPResponse,
    OCSPResponseStatus,
)

from ....._typing import ProxyType
from .....exceptions import RequestException, SSLError
from .....models import PreparedRequest
from .....packages.urllib3 import ConnectionInfo
from .....packages.urllib3.contrib.resolver._async import AsyncBaseResolver
from .....packages.urllib3.exceptions import SecurityWarning
from .....utils import is_cancelled_error_root_cause
from .. import (
    _parse_x509_der_cached,
    _str_fingerprint_of,
    readable_revocation_reason,
)


class InMemoryRevocationStatus:
    def __init__(self, max_size: int = 2048):
        self._max_size: int = max_size
        self._store: dict[str, OCSPResponse] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._issuers_map: dict[str, Certificate] = {}
        self._timings: list[datetime.datetime] = []
        self._failure_count: int = 0
        self.hold: bool = False

    @staticmethod
    def support_pickle() -> bool:
        """This gives you a hint on whether you can cache it to restore later."""
        return hasattr(OCSPResponse, "serialize")

    def __getstate__(self) -> dict[str, typing.Any]:
        return {
            "_max_size": self._max_size,
            "_store": {k: v.serialize() for k, v in self._store.items()},
            "_issuers_map": {k: v.serialize() for k, v in self._issuers_map.items()},
            "_failure_count": self._failure_count,
        }

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        if "_store" not in state or "_issuers_map" not in state or "_max_size" not in state:
            raise OSError("unrecoverable state for InMemoryRevocationStatus")

        self.hold = False
        self._timings = []

        self._max_size = state["_max_size"]
        self._failure_count = state["_failure_count"] if "_failure_count" in state else 0

        self._store = {}
        self._semaphores = {}

        for k, v in state["_store"].items():
            self._store[k] = OCSPResponse.deserialize(v)
            self._semaphores[k] = asyncio.Semaphore()

        self._issuers_map = {}

        for k, v in state["_issuers_map"].items():
            self._issuers_map[k] = Certificate.deserialize(v)

    def get_issuer_of(self, peer_certificate: Certificate) -> Certificate | None:
        fingerprint: str = _str_fingerprint_of(peer_certificate)

        if fingerprint not in self._issuers_map:
            return None

        return self._issuers_map[fingerprint]

    def __len__(self) -> int:
        return len(self._store)

    def incr_failure(self) -> None:
        self._failure_count += 1

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @asynccontextmanager
    async def lock(self, peer_certificate: Certificate) -> typing.AsyncGenerator[None, None]:
        fingerprint: str = _str_fingerprint_of(peer_certificate)

        if fingerprint not in self._semaphores:
            self._semaphores[fingerprint] = asyncio.Semaphore()

        await self._semaphores[fingerprint].acquire()

        try:
            yield
        finally:
            self._semaphores[fingerprint].release()

    def rate(self):
        previous_dt: datetime.datetime | None = None
        delays: list[float] = []

        for dt in self._timings:
            if previous_dt is None:
                previous_dt = dt
                continue
            delays.append((dt - previous_dt).total_seconds())
            previous_dt = dt

        return sum(delays) / len(delays) if delays else 0.0

    def check(self, peer_certificate: Certificate) -> OCSPResponse | None:
        fingerprint: str = _str_fingerprint_of(peer_certificate)

        if fingerprint not in self._store:
            return None

        cached_response = self._store[fingerprint]

        if cached_response.certificate_status == OCSPCertStatus.GOOD:
            if cached_response.next_update and datetime.datetime.now().timestamp() >= cached_response.next_update:
                del self._store[fingerprint]
                return None
            return cached_response

        return cached_response

    def save(
        self,
        peer_certificate: Certificate,
        issuer_certificate: Certificate,
        ocsp_response: OCSPResponse,
    ) -> None:
        if len(self._store) >= self._max_size:
            tbd_key: str | None = None
            closest_next_update: int | None = None

            for k in self._store:
                if self._store[k].response_status != OCSPResponseStatus.SUCCESSFUL:
                    tbd_key = k
                    break

                if self._store[k].certificate_status != OCSPCertStatus.REVOKED:
                    if closest_next_update is None:
                        closest_next_update = self._store[k].next_update
                        tbd_key = k
                        continue
                    if self._store[k].next_update > closest_next_update:  # type: ignore
                        closest_next_update = self._store[k].next_update
                        tbd_key = k

            if tbd_key:
                del self._store[tbd_key]
                del self._issuers_map[tbd_key]
            else:
                first_key = list(self._store.keys())[0]
                del self._store[first_key]
                del self._issuers_map[first_key]

        peer_fingerprint: str = _str_fingerprint_of(peer_certificate)

        self._store[peer_fingerprint] = ocsp_response
        self._issuers_map[peer_fingerprint] = issuer_certificate
        self._failure_count = 0

        self._timings.append(datetime.datetime.now())

        if len(self._timings) >= self._max_size:
            self._timings.pop(0)


async def verify(
    r: PreparedRequest,
    strict: bool = False,
    timeout: float | int = 0.2,
    proxies: ProxyType | None = None,
    resolver: AsyncBaseResolver | None = None,
    happy_eyeballs: bool | int = False,
    cache: InMemoryRevocationStatus | None = None,
) -> None:
    conn_info: ConnectionInfo | None = r.conn_info

    # we can't do anything in that case.
    if conn_info is None or conn_info.certificate_der is None or conn_info.certificate_dict is None:
        return

    endpoints: list[str] = [  # type: ignore
        # exclude non-HTTP endpoint. like ldap.
        ep  # type: ignore
        for ep in list(conn_info.certificate_dict.get("OCSP", []))  # type: ignore
        if ep.startswith("http://")  # type: ignore
    ]

    # well... not all issued certificate have a OCSP entry. e.g. mkcert.
    if not endpoints:
        return

    if cache is None:
        cache = InMemoryRevocationStatus()

    peer_certificate = _parse_x509_der_cached(conn_info.certificate_der)

    async with cache.lock(peer_certificate):
        # this feature, by default, is reserved for a reasonable usage.
        if not strict:
            if cache.failure_count >= 4:
                return

            mean_rate_sec = cache.rate()
            cache_count = len(cache)

            if cache_count >= 10 and mean_rate_sec <= 1.0:
                cache.hold = True

            if cache.hold:
                return

        # some corporate environment
        # have invalid OCSP implementation
        # they use a cert that IS NOT in the chain
        # to sign the response. It's weird but true.
        # see https://github.com/jawah/niquests/issues/274
        ignore_signature_without_strict = ipaddress.ip_address(conn_info.destination_address[0]).is_private or bool(proxies)
        verify_signature = strict is True or ignore_signature_without_strict is False

        cached_response = cache.check(peer_certificate)

        if cached_response is not None:
            issuer_certificate = cache.get_issuer_of(peer_certificate)

            if issuer_certificate:
                conn_info.issuer_certificate_der = issuer_certificate.public_bytes()

            if cached_response.response_status == OCSPResponseStatus.SUCCESSFUL:
                if cached_response.certificate_status == OCSPCertStatus.REVOKED:
                    r.ocsp_verified = False
                    raise SSLError(
                        (
                            f"Unable to establish a secure connection to {r.url} because the certificate has been revoked "
                            f"by issuer ({readable_revocation_reason(cached_response.revocation_reason) or 'unspecified'}). "
                            "You should avoid trying to request anything from it as the remote has been compromised. ",
                            "See https://niquests.readthedocs.io/en/latest/user/advanced.html#ocsp-or-certificate-revocation "
                            "for more information.",
                        )
                    )
                elif cached_response.certificate_status == OCSPCertStatus.UNKNOWN:
                    r.ocsp_verified = False
                    if strict is True:
                        raise SSLError(
                            f"Unable to establish a secure connection to {r.url} because the issuer does not know "
                            "whether certificate is valid or not. This error occurred because you enabled strict mode "
                            "for the OCSP / Revocation check."
                        )
                else:
                    r.ocsp_verified = True

            return

        from .....async_session import AsyncSession

        async with AsyncSession(resolver=resolver, happy_eyeballs=happy_eyeballs) as session:
            session.trust_env = False
            if proxies:
                session.proxies = proxies

            # When using Python native capabilities, you won't have the issuerCA DER by default (Python 3.7 to 3.9).
            # Unfortunately! But no worries, we can circumvent it! (Python 3.10+ is not concerned anymore)
            # Three ways are valid to fetch it (in order of preference, safest to riskiest):
            #   - The issuer can be (but unlikely) a root CA.
            #   - Retrieve it by asking it from the TLS layer.
            #   - Downloading it using specified caIssuers from the peer certificate.
            if conn_info.issuer_certificate_der is None:
                # It could be a root (self-signed) certificate. Or a previously seen issuer.
                issuer_certificate = cache.get_issuer_of(peer_certificate)

                hint_ca_issuers: list[str] = [
                    ep  # type: ignore
                    for ep in list(conn_info.certificate_dict.get("caIssuers", []))  # type: ignore
                    if ep.startswith("http://")  # type: ignore
                ]

                if issuer_certificate is None and hint_ca_issuers:
                    try:
                        raw_intermediary_response = await session.get(hint_ca_issuers[0])
                    except RequestException as e:
                        if is_cancelled_error_root_cause(e):
                            return
                    except asyncio.CancelledError:  # don't raise any error or warnings!
                        return
                    else:
                        if raw_intermediary_response.status_code and 300 > raw_intermediary_response.status_code >= 200:
                            raw_intermediary_content = raw_intermediary_response.content

                            if raw_intermediary_content is not None:
                                # binary DER
                                if b"-----BEGIN CERTIFICATE-----" not in raw_intermediary_content:
                                    issuer_certificate = Certificate(raw_intermediary_content)
                                # b64 PEM
                                elif b"-----BEGIN CERTIFICATE-----" in raw_intermediary_content:
                                    issuer_certificate = Certificate(
                                        ssl.PEM_cert_to_DER_cert(raw_intermediary_content.decode())
                                    )

                # Well! We're out of luck. No further should we go.
                if issuer_certificate is None:
                    cache.incr_failure()
                    if strict:
                        warnings.warn(
                            (
                                f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate "
                                "via OCSP. You are seeing this warning due to enabling strict mode for OCSP / "
                                "Revocation check. Reason: Remote did not provide any intermediary certificate."
                            ),
                            SecurityWarning,
                        )
                    return

                conn_info.issuer_certificate_der = issuer_certificate.public_bytes()
            else:
                issuer_certificate = Certificate(conn_info.issuer_certificate_der)

            try:
                req = OCSPRequest(peer_certificate.public_bytes(), issuer_certificate.public_bytes())
            except ValueError:
                if strict:
                    warnings.warn(
                        (
                            f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP. "
                            "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                            "Reason: The X509 OCSP generator failed to assemble the request."
                        ),
                        SecurityWarning,
                    )
                return

            try:
                ocsp_http_response = await session.post(
                    endpoints[randint(0, len(endpoints) - 1)],
                    data=req.public_bytes(),
                    headers={"Content-Type": "application/ocsp-request"},
                    timeout=timeout,
                )
            except RequestException as e:
                if is_cancelled_error_root_cause(e):
                    return
                cache.incr_failure()
                if strict:
                    warnings.warn(
                        (
                            f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP. "
                            "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                            f"Reason: {e}"
                        ),
                        SecurityWarning,
                    )
                return
            except asyncio.CancelledError:  # don't raise any error or warnings!
                return

            if ocsp_http_response.status_code and 300 > ocsp_http_response.status_code >= 200:
                if ocsp_http_response.content is None:
                    return

                try:
                    ocsp_resp = OCSPResponse(ocsp_http_response.content)
                except ValueError:
                    if strict:
                        warnings.warn(
                            (
                                f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP. "
                                "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                                "Reason: The X509 OCSP parser failed to read the response"
                            ),
                            SecurityWarning,
                        )
                    return

                if verify_signature:
                    # Verify the signature of the OCSP response with issuer public key
                    try:
                        if not ocsp_resp.authenticate_for(issuer_certificate.public_bytes()):  # type: ignore[attr-defined]
                            raise SSLError(
                                f"Unable to establish a secure connection to {r.url} "
                                "because the OCSP response received has been tampered. "
                                "You could be targeted by a MITM attack."
                            )
                    except ValueError:
                        if strict:
                            warnings.warn(
                                (
                                    f"Unable to insure that the remote peer ({r.url}) has a currently "
                                    "valid certificate via OCSP. You are seeing this warning due to "
                                    "enabling strict mode for OCSP / Revocation check. "
                                    "Reason: The X509 OCSP response is signed using an unsupported algorithm."
                                ),
                                SecurityWarning,
                            )

                cache.save(peer_certificate, issuer_certificate, ocsp_resp)

                if ocsp_resp.response_status == OCSPResponseStatus.SUCCESSFUL:
                    if ocsp_resp.certificate_status == OCSPCertStatus.REVOKED:
                        r.ocsp_verified = False
                        raise SSLError(
                            f"Unable to establish a secure connection to {r.url} because the certificate has been revoked "
                            f"by issuer ({readable_revocation_reason(ocsp_resp.revocation_reason) or 'unspecified'}). "
                            "You should avoid trying to request anything from it as the remote has been compromised. "
                            "See https://niquests.readthedocs.io/en/latest/user/advanced.html#ocsp-or-certificate-revocation "
                            "for more information."
                        )
                    if ocsp_resp.certificate_status == OCSPCertStatus.UNKNOWN:
                        r.ocsp_verified = False
                        if strict is True:
                            raise SSLError(
                                f"Unable to establish a secure connection to {r.url} because the issuer does not know whether "
                                "certificate is valid or not. This error occurred because you enabled strict mode for "
                                "the OCSP / Revocation check."
                            )
                    else:
                        r.ocsp_verified = True
                else:
                    if strict:
                        warnings.warn(
                            (
                                f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP. "
                                "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                                f"OCSP Server Status: {ocsp_resp.response_status}"
                            ),
                            SecurityWarning,
                        )
            else:
                if strict:
                    warnings.warn(
                        (
                            f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP. "
                            "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                            f"OCSP Server Status: {str(ocsp_http_response)}"
                        ),
                        SecurityWarning,
                    )


__all__ = ("verify",)
