from __future__ import annotations

import datetime
import typing
import warnings
from random import randint
from statistics import mean

if typing.TYPE_CHECKING:
    from ..sessions import Session

import hmac
import socket
import threading
from hashlib import sha256

import wassima
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.x509 import (
    Certificate,
    load_der_x509_certificate,
    load_pem_x509_certificate,
    ocsp,
)
from urllib3 import ConnectionInfo
from urllib3.exceptions import SecurityWarning
from urllib3.util.url import parse_url

from ..exceptions import RequestException, SSLError
from ..models import PreparedRequest
from ._picotls import (
    ALERT,
    CHANGE_CIPHER,
    HANDSHAKE,
    derive_secret,
    gen_client_hello,
    handle_encrypted_extensions,
    handle_server_cert,
    handle_server_hello,
    multiply_num_on_ec_point,
    num_to_bytes,
    recv_tls,
    recv_tls_and_decrypt,
    send_tls,
)


def _str_fingerprint_of(certificate: Certificate) -> str:
    return ":".join([format(i, "02x") for i in certificate.fingerprint(SHA1())])


def _infer_issuer_from(certificate: Certificate) -> Certificate | None:
    issuer: Certificate | None = None

    for der_cert in wassima.root_der_certificates() + _SharedStaplingCache.issuers:
        if isinstance(der_cert, Certificate):
            possible_issuer = der_cert
        else:
            possible_issuer = load_der_x509_certificate(der_cert)

        try:
            certificate.verify_directly_issued_by(possible_issuer)
        except ValueError:
            continue
        else:
            issuer = possible_issuer
            break

    return issuer


def _ask_nicely_for_issuer(
    hostname: str, dst_address: tuple[str, int], timeout: int | float = 0.2
) -> Certificate | None:
    """When encountering a problem in development, one should always say that there is many solutions.
    From dirtiest to the cleanest, not always known but with progressive effort, we'll eventually land at the cleanest.

    This function do a manual TLS 1.2+ handshake till we extract certificates from the remote peer. Does not
    need to be secure, we just have to retrieve the issuer cert if any."""
    if dst_address[0].count(".") == 3:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    sock.connect(dst_address)
    sock.settimeout(timeout)

    SECP256R1_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    SECP256R1_A = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC
    SECP256R1_G = (
        0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
        0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
    )

    randelem = [b"\xAC", b"\xDC", b"\xFA", b"\xAF"]
    client_random = b"".join([randelem[randint(0, 3)] for e in range(32)])
    our_ecdh_privkey = randint(42, 98)
    our_ecdh_pubkey_x, our_ecdh_pubkey_y = multiply_num_on_ec_point(
        our_ecdh_privkey, SECP256R1_G[0], SECP256R1_G[1], SECP256R1_A, SECP256R1_P
    )

    client_hello = gen_client_hello(
        hostname, client_random, our_ecdh_pubkey_x, our_ecdh_pubkey_y
    )

    send_tls(sock, HANDSHAKE, client_hello)

    rec_type, server_hello = recv_tls(sock)

    if not rec_type == HANDSHAKE:
        sock.close()
        return None

    (
        server_random,
        session_id,
        server_ecdh_pubkey_x,
        server_ecdh_pubkey_y,
    ) = handle_server_hello(server_hello)

    rec_type, server_change_cipher = recv_tls(sock)

    if not rec_type == CHANGE_CIPHER:
        sock.close()
        return None

    our_secret_point_x = multiply_num_on_ec_point(
        our_ecdh_privkey,
        server_ecdh_pubkey_x,
        server_ecdh_pubkey_y,
        SECP256R1_A,
        SECP256R1_P,
    )[0]
    our_secret = num_to_bytes(our_secret_point_x, 32)

    early_secret = hmac.new(b"", b"\x00" * 32, sha256).digest()
    preextractsec = derive_secret(
        b"derived", key=early_secret, data=sha256(b"").digest(), hash_len=32
    )
    handshake_secret = hmac.new(preextractsec, our_secret, sha256).digest()
    hello_hash = sha256(client_hello + server_hello).digest()
    server_hs_secret = derive_secret(
        b"s hs traffic", key=handshake_secret, data=hello_hash, hash_len=32
    )
    server_write_key = derive_secret(
        b"key", key=server_hs_secret, data=b"", hash_len=16
    )
    server_write_iv = derive_secret(b"iv", key=server_hs_secret, data=b"", hash_len=12)

    server_seq_num = 0

    rec_type, encrypted_extensions = recv_tls_and_decrypt(
        sock, server_write_key, server_write_iv, server_seq_num
    )

    if not rec_type == HANDSHAKE:
        sock.close()
        return None

    server_seq_num += 1

    remaining_bytes = handle_encrypted_extensions(encrypted_extensions)

    if not remaining_bytes:
        rec_type, server_cert = recv_tls_and_decrypt(
            sock, server_write_key, server_write_iv, server_seq_num
        )
    else:
        rec_type, server_cert = rec_type, remaining_bytes

    if not rec_type == HANDSHAKE:
        sock.close()
        return None

    server_seq_num += 1

    der_certificates = handle_server_cert(server_cert)
    certificates = []

    for der in der_certificates:
        certificates.append(load_der_x509_certificate(der))

    send_tls(sock, ALERT, b"\x01\x00")
    sock.close()

    if len(certificates) <= 1:
        return None

    # kept in order, the immediate issuer come just after the leaf one.
    return certificates[1]


class InMemoryRevocationStatus:
    def __init__(self, max_size: int = 2048):
        self._max_size: int = max_size
        self._store: dict[str, ocsp.OCSPResponse] = {}
        self._issuers: list[Certificate] = []
        self._timings: list[datetime.datetime] = []
        self._access_lock: threading.Lock = threading.Lock()
        self.hold: bool = False

    @property
    def issuers(self) -> list[Certificate]:
        with self._access_lock:
            return self._issuers

    def __len__(self) -> int:
        with self._access_lock:
            return len(self._store)

    def rate(self):
        with self._access_lock:
            previous_dt: datetime.datetime | None = None
            delays: list[float] = []

            for dt in self._timings:
                if previous_dt is None:
                    previous_dt = dt
                    continue
                delays.append((dt - previous_dt).total_seconds())
                previous_dt = dt

            return mean(delays) if delays else 0.0

    def check(self, peer_certificate: Certificate) -> ocsp.OCSPResponse | None:
        with self._access_lock:
            fingerprint: str = _str_fingerprint_of(peer_certificate)

            if fingerprint not in self._store:
                return None

            cached_response = self._store[fingerprint]

            if cached_response.certificate_status == ocsp.OCSPCertStatus.GOOD:
                if (
                    cached_response.next_update
                    and datetime.datetime.now().timestamp()
                    >= cached_response.next_update.timestamp()
                ):
                    del self._store[fingerprint]
                    return None
                return cached_response

            return cached_response

    def save(
        self,
        peer_certificate: Certificate,
        issuer_certificate: Certificate,
        ocsp_response: ocsp.OCSPResponse,
    ) -> None:
        with self._access_lock:
            if len(self._store) >= self._max_size:
                tbd_key: str | None = None
                closest_next_update: datetime.datetime | None = None

                for k in self._store:
                    if (
                        self._store[k].response_status
                        != ocsp.OCSPResponseStatus.SUCCESSFUL
                    ):
                        tbd_key = k
                        break

                    if self._store[k].certificate_status != ocsp.OCSPCertStatus.REVOKED:
                        if closest_next_update is None:
                            closest_next_update = self._store[k].next_update
                            tbd_key = k
                            continue
                        if self._store[k].next_update > closest_next_update:  # type: ignore
                            closest_next_update = self._store[k].next_update
                            tbd_key = k

                if tbd_key:
                    del self._store[tbd_key]
                else:
                    del self._store[list(self._store.keys())[0]]

            self._store[_str_fingerprint_of(peer_certificate)] = ocsp_response

            issuer_fingerprint = _str_fingerprint_of(issuer_certificate)

            if not any(
                _str_fingerprint_of(c) == issuer_fingerprint for c in self._issuers
            ):
                self._issuers.append(issuer_certificate)

            if len(self._issuers) >= self._max_size:
                self._issuers.pop(0)

            self._timings.append(datetime.datetime.now())

            if len(self._timings) >= self._max_size:
                self._timings.pop(0)


_SharedStaplingCache = InMemoryRevocationStatus()


def verify(
    session: Session,
    r: PreparedRequest,
    strict: bool = False,
    timeout: float | int = 0.2,
) -> None:
    conn_info: ConnectionInfo | None = r.conn_info

    # we can't do anything in that case.
    if (
        conn_info is None
        or conn_info.certificate_der is None
        or conn_info.certificate_dict is None
    ):
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

    # this feature, by default, is reserved for a reasonable usage.
    if not strict:
        mean_rate_sec = _SharedStaplingCache.rate()
        cache_count = len(_SharedStaplingCache)

        if cache_count >= 10 and mean_rate_sec <= 1.0:
            _SharedStaplingCache.hold = True

        if _SharedStaplingCache.hold:
            return

    peer_certificate = load_der_x509_certificate(conn_info.certificate_der)
    cached_response = _SharedStaplingCache.check(peer_certificate)

    if cached_response is not None:
        issuer_certificate = _infer_issuer_from(peer_certificate)

        if issuer_certificate:
            conn_info.issuer_certificate_der = issuer_certificate.public_bytes(
                serialization.Encoding.DER
            )

        if cached_response.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL:
            if cached_response.certificate_status == ocsp.OCSPCertStatus.REVOKED:
                r.ocsp_verified = False
                raise SSLError(
                    f"""Unable to establish a secure connection to {r.url} because the certificate has been revoked
                    by issuer ({cached_response.revocation_reason}).
                    You should avoid trying to request anything from it as the remote has been compromised.
                    See https://en.wikipedia.org/wiki/OCSP_stapling for more information."""
                )
            elif cached_response.certificate_status == ocsp.OCSPCertStatus.UNKNOWN:
                r.ocsp_verified = False
                if strict is True:
                    raise SSLError(
                        f"""Unable to establish a secure connection to {r.url} because the issuer does not know whether
                        certificate is valid or not. This error occurred because you enabled strict mode for
                        the OCSP / Revocation check."""
                    )
            else:
                r.ocsp_verified = True

        return

    # When using Python native capabilities, you won't have the issuerCA DER by default.
    # Unfortunately! But no worries, we can circumvent it!
    # Three ways are valid to fetch it (in order of preference, safest to riskiest):
    #   - The issuer can be (but unlikely) a root CA.
    #   - Retrieve it by asking it from the TLS layer.
    #   - Downloading it using specified caIssuers from the peer certificate.
    if conn_info.issuer_certificate_der is None:
        # It could be a root (self-signed) certificate. Or a previously seen issuer.
        issuer_certificate = _infer_issuer_from(peer_certificate)

        # If not, try to ask nicely the remote to give us the certificate chain, and extract
        # from it the immediate issuer.
        if issuer_certificate is None:
            try:
                if r.url is None:
                    raise ValueError

                url_parsed = parse_url(r.url)

                if url_parsed.hostname is None or conn_info.destination_address is None:
                    raise ValueError

                issuer_certificate = _ask_nicely_for_issuer(
                    url_parsed.hostname,
                    conn_info.destination_address,
                    timeout,
                )

                if issuer_certificate is not None:
                    peer_certificate.verify_directly_issued_by(issuer_certificate)

            except (socket.gaierror, TimeoutError, ConnectionError):
                pass
            except ValueError:
                issuer_certificate = None

        hint_ca_issuers: list[str] = [ep for ep in list(conn_info.certificate_dict.get("caIssuers", [])) if ep.startswith("http://")]  # type: ignore

        if issuer_certificate is None and hint_ca_issuers:
            try:
                raw_intermediary_response = session.get(hint_ca_issuers[0])
            except RequestException:
                pass
            else:
                if (
                    raw_intermediary_response.status_code
                    and 300 > raw_intermediary_response.status_code >= 200
                ):
                    raw_intermediary_content = raw_intermediary_response.content

                    if raw_intermediary_content is not None:
                        # binary DER
                        if (
                            b"-----BEGIN CERTIFICATE-----"
                            not in raw_intermediary_content
                        ):
                            issuer_certificate = load_der_x509_certificate(
                                raw_intermediary_content
                            )
                        # b64 PEM
                        elif b"-----BEGIN CERTIFICATE-----" in raw_intermediary_content:
                            issuer_certificate = load_pem_x509_certificate(
                                raw_intermediary_content
                            )

        # Well! We're out of luck. No further should we go.
        if issuer_certificate is None:
            if strict:
                warnings.warn(
                    f"""Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP.
                    You are seeing this warning due to enabling strict mode for OCSP / Revocation check.
                    Reason: Remote did not provide any intermediaries certificate.""",
                    SecurityWarning,
                )
            return

        conn_info.issuer_certificate_der = issuer_certificate.public_bytes(
            serialization.Encoding.DER
        )
    else:
        issuer_certificate = load_der_x509_certificate(conn_info.issuer_certificate_der)

    builder = ocsp.OCSPRequestBuilder()
    builder = builder.add_certificate(peer_certificate, issuer_certificate, SHA1())

    req = builder.build()

    try:
        ocsp_http_response = session.post(
            endpoints[randint(0, len(endpoints) - 1)],
            data=req.public_bytes(serialization.Encoding.DER),
            headers={"Content-Type": "application/ocsp-request"},
            timeout=timeout,
        )
    except RequestException as e:
        if strict:
            warnings.warn(
                f"""Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP.
                You are seeing this warning due to enabling strict mode for OCSP / Revocation check.
                Reason: {e}""",
                SecurityWarning,
            )
        return

    if ocsp_http_response.status_code and 300 > ocsp_http_response.status_code >= 200:
        if ocsp_http_response.content is None:
            return

        ocsp_resp = ocsp.load_der_ocsp_response(ocsp_http_response.content)

        _SharedStaplingCache.save(peer_certificate, issuer_certificate, ocsp_resp)

        if ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL:
            if ocsp_resp.certificate_status == ocsp.OCSPCertStatus.REVOKED:
                r.ocsp_verified = False
                raise SSLError(
                    f"""Unable to establish a secure connection to {r.url} because the certificate has been revoked
                    by issuer ({ocsp_resp.revocation_reason}).
                    You should avoid trying to request anything from it as the remote has been compromised.
                    See https://en.wikipedia.org/wiki/OCSP_stapling for more information."""
                )
            if ocsp_resp.certificate_status == ocsp.OCSPCertStatus.UNKNOWN:
                r.ocsp_verified = False
                if strict is True:
                    raise SSLError(
                        f"""Unable to establish a secure connection to {r.url} because the issuer does not know whether
                        certificate is valid or not. This error occurred because you enabled strict mode for
                        the OCSP / Revocation check."""
                    )
            else:
                r.ocsp_verified = True
        else:
            if strict:
                warnings.warn(
                    f"""Unable to insure that the remote peer ({r.url}) has a currently valid certificate via OCSP.
                    You are seeing this warning due to enabling strict mode for OCSP / Revocation check.
                    OCSP Server Status: {ocsp_resp.response_status}""",
                    SecurityWarning,
                )


__all__ = ("verify",)
