from __future__ import annotations

import asyncio
import datetime
import ipaddress
import ssl
import typing
import warnings
from random import randint

from qh3._hazmat import (
    Certificate,
    CertificateRevocationList,
)

from ....._typing import ProxyType
from .....exceptions import RequestException, SSLError
from .....models import PreparedRequest
from .....packages.urllib3 import ConnectionInfo
from .....packages.urllib3.contrib.resolver._async import AsyncBaseResolver
from .....packages.urllib3.exceptions import SecurityWarning
from .....utils import is_cancelled_error_root_cause
from ..._ocsp import _parse_x509_der_cached, _str_fingerprint_of, readable_revocation_reason


class InMemoryRevocationList:
    def __init__(self, max_size: int = 256):
        self._max_size: int = max_size
        self._store: dict[str, CertificateRevocationList] = {}
        self._issuers_map: dict[str, Certificate] = {}
        self._crl_endpoints: dict[str, str] = {}
        self._failure_count: int = 0

    def __getstate__(self) -> dict[str, typing.Any]:
        return {
            "_max_size": self._max_size,
            "_store": {k: v.serialize() for k, v in self._store.items()},
            "_issuers_map": {k: v.serialize() for k, v in self._issuers_map.items()},
            "_failure_count": self._failure_count,
            "_crl_endpoints": self._crl_endpoints,
        }

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        if "_store" not in state or "_issuers_map" not in state or "_max_size" not in state or "_crl_endpoints" not in state:
            raise OSError("unrecoverable state for InMemoryRevocationStatus")

        self._max_size = state["_max_size"]
        self._failure_count = state["_failure_count"] if "_failure_count" in state else 0
        self._crl_endpoints = state["_crl_endpoints"]

        self._store = {}

        for k, v in state["_store"].items():
            self._store[k] = CertificateRevocationList.deserialize(v)

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

    def check(self, crl_distribution_point: str) -> CertificateRevocationList | None:
        if crl_distribution_point not in self._store:
            return None

        cached_response = self._store[crl_distribution_point]

        if cached_response.next_update_at and datetime.datetime.now().timestamp() >= cached_response.next_update_at:
            del self._store[crl_distribution_point]
            return None

        return cached_response

    def get_previous_crl_endpoint(self, leaf: Certificate) -> str | None:
        fingerprint = _str_fingerprint_of(leaf)

        if fingerprint in self._crl_endpoints:
            return self._crl_endpoints[fingerprint]

        return None

    def save(
        self,
        leaf: Certificate,
        issuer: Certificate,
        crl: CertificateRevocationList,
        crl_distribution_point: str,
    ) -> None:
        if len(self._store) >= self._max_size:
            tbd_key: str | None = None
            closest_next_update: int | None = None

            for k in self._store:
                if closest_next_update is None:
                    closest_next_update = self._store[k].next_update_at
                    tbd_key = k
                    continue
                if self._store[k].next_update_at > closest_next_update:  # type: ignore
                    closest_next_update = self._store[k].next_update_at
                    tbd_key = k

            if tbd_key:
                del self._store[tbd_key]
            else:
                first_key = list(self._store.keys())[0]
                del self._store[first_key]

        peer_fingerprint: str = _str_fingerprint_of(leaf)

        self._store[crl_distribution_point] = crl
        self._crl_endpoints[peer_fingerprint] = crl_distribution_point
        self._issuers_map[peer_fingerprint] = issuer
        self._failure_count = 0


async def verify(
    r: PreparedRequest,
    strict: bool = False,
    timeout: float | int = 0.2,
    proxies: ProxyType | None = None,
    resolver: AsyncBaseResolver | None = None,
    happy_eyeballs: bool | int = False,
    cache: InMemoryRevocationList | None = None,
) -> None:
    conn_info: ConnectionInfo | None = r.conn_info

    # we can't do anything in that case.
    if conn_info is None or conn_info.certificate_der is None or conn_info.certificate_dict is None:
        return

    endpoints: list[str] = [  # type: ignore
        # exclude non-HTTP endpoint. like ldap.
        ep  # type: ignore
        for ep in list(conn_info.certificate_dict.get("crlDistributionPoints", []))  # type: ignore
        if ep.startswith("http://")  # type: ignore
    ]

    # well... not all issued certificate have a OCSP entry. e.g. mkcert.
    if not endpoints:
        return

    if cache is None:
        cache = InMemoryRevocationList()

    if not strict:
        if cache.failure_count >= 4:
            return

    # some corporate environment
    # have invalid OCSP implementation
    # they use a cert that IS NOT in the chain
    # to sign the response. It's weird but true.
    # see https://github.com/jawah/niquests/issues/274
    ignore_signature_without_strict = ipaddress.ip_address(conn_info.destination_address[0]).is_private or bool(proxies)
    verify_signature = strict is True or ignore_signature_without_strict is False

    peer_certificate: Certificate = _parse_x509_der_cached(conn_info.certificate_der)

    crl_distribution_point: str = cache.get_previous_crl_endpoint(peer_certificate) or endpoints[randint(0, len(endpoints) - 1)]

    cached_revocation_list = cache.check(crl_distribution_point)

    if cached_revocation_list is not None:
        issuer_certificate = cache.get_issuer_of(peer_certificate)

        if issuer_certificate is not None:
            conn_info.issuer_certificate_der = issuer_certificate.public_bytes()

        revocation_status = cached_revocation_list.is_revoked(peer_certificate.serial_number)

        if revocation_status is not None:
            r.ocsp_verified = False
            raise SSLError(
                (
                    f"Unable to establish a secure connection to {r.url} because the certificate has been revoked "
                    f"by issuer ({readable_revocation_reason(revocation_status.reason)}). "
                    "You should avoid trying to request anything from it as the remote has been compromised. ",
                    "See https://niquests.readthedocs.io/en/latest/user/advanced.html#ocsp-or-certificate-revocation "
                    "for more information.",
                )
            )
        else:
            r.ocsp_verified = True

        return

    from .....async_session import AsyncSession

    async with AsyncSession(resolver=resolver, happy_eyeballs=happy_eyeballs) as session:
        session.trust_env = False
        if proxies:
            session.proxies = proxies

        # When using Python native capabilities, you won't have the issuerCA DER by default.
        # Unfortunately! But no worries, we can circumvent it!
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
                                issuer_certificate = Certificate(ssl.PEM_cert_to_DER_cert(raw_intermediary_content.decode()))

            # Well! We're out of luck. No further should we go.
            if issuer_certificate is None:
                # aia fetching should be counted as general ocsp failure too.
                cache.incr_failure()
                if strict:
                    warnings.warn(
                        (
                            f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate "
                            "via CRL. You are seeing this warning due to enabling strict mode for OCSP / "
                            "Revocation check. Reason: Remote did not provide any intermediary certificate."
                        ),
                        SecurityWarning,
                    )
                return

            conn_info.issuer_certificate_der = issuer_certificate.public_bytes()
        else:
            issuer_certificate = Certificate(conn_info.issuer_certificate_der)

        try:
            crl_http_response = await session.get(
                crl_distribution_point,
                timeout=timeout,
            )
        except RequestException as e:
            if is_cancelled_error_root_cause(e):
                return
            # aia fetching should be counted as general ocsp failure too.
            cache.incr_failure()
            if strict:
                warnings.warn(
                    (
                        f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via CRL. "
                        "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                        f"Reason: {e}"
                    ),
                    SecurityWarning,
                )
            return
        except asyncio.CancelledError:  # don't raise any error or warnings!
            return

        if crl_http_response.status_code and 300 > crl_http_response.status_code >= 200:
            if crl_http_response.content is None:
                return

            try:
                crl = CertificateRevocationList(crl_http_response.content)
            except ValueError:
                if strict:
                    warnings.warn(
                        (
                            f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via CRL. "
                            "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                            "Reason: The X509 CRL parser failed to read the response"
                        ),
                        SecurityWarning,
                    )
                return

            if verify_signature:
                # Verify the signature of the OCSP response with issuer public key
                try:
                    if not crl.authenticate_for(issuer_certificate.public_bytes()):
                        raise SSLError(
                            f"Unable to establish a secure connection to {r.url} "
                            "because the CRL response received has been tampered. "
                            "You could be targeted by a MITM attack."
                        )
                except ValueError:
                    if strict:
                        warnings.warn(
                            (
                                f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via CRL. "
                                "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                                "Reason: The X509 CRL is signed using an unsupported algorithm."
                            ),
                            SecurityWarning,
                        )

            cache.save(peer_certificate, issuer_certificate, crl, crl_distribution_point)

            revocation_status = crl.is_revoked(peer_certificate.serial_number)

            if revocation_status is not None:
                r.ocsp_verified = False
                raise SSLError(
                    f"Unable to establish a secure connection to {r.url} because the certificate has been revoked "
                    f"by issuer ({readable_revocation_reason(revocation_status.reason)}). "
                    "You should avoid trying to request anything from it as the remote has been compromised. "
                    "See https://niquests.readthedocs.io/en/latest/user/advanced.html#ocsp-or-certificate-revocation "
                    "for more information."
                )
            else:
                r.ocsp_verified = True
        else:
            if strict:
                warnings.warn(
                    (
                        f"Unable to insure that the remote peer ({r.url}) has a currently valid certificate via CRL. "
                        "You are seeing this warning due to enabling strict mode for OCSP / Revocation check. "
                        f"CRL endpoint: {str(crl_http_response)}"
                    ),
                    SecurityWarning,
                )


__all__ = ("verify",)
