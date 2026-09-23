from __future__ import annotations

import argparse
import socket
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import ocsp

from . import CRL_PORT, LEAVES, OCSP_URL, utc_time


def _validate_crl(crl: x509.CertificateRevocationList, issuer: x509.Certificate) -> None:
    if crl.issuer != issuer.subject or not crl.is_signature_valid(issuer.public_key()):
        raise ValueError("The served CRL signature is invalid")
    now = datetime.now(timezone.utc)
    this_update, next_update = utc_time(crl, "last_update"), utc_time(crl, "next_update")
    if this_update is None or next_update is None or not this_update <= now < next_update:
        raise ValueError("The served CRL is not currently valid")


def _validate_ocsp(
    reply: ocsp.OCSPResponse,
    request: ocsp.OCSPRequest,
    signer: x509.Certificate,
    status: ocsp.OCSPCertStatus,
) -> None:
    if reply.response_status != ocsp.OCSPResponseStatus.SUCCESSFUL:
        raise ValueError(f"OCSP readiness failed: {reply.response_status}")
    if (
        reply.serial_number != request.serial_number
        or reply.hash_algorithm.name != request.hash_algorithm.name
        or reply.issuer_name_hash != request.issuer_name_hash
        or reply.issuer_key_hash != request.issuer_key_hash
        or reply.certificate_status != status
        or list(reply.certificates) != [signer]
        or reply.responder_key_hash != x509.SubjectKeyIdentifier.from_public_key(signer.public_key()).digest
    ):
        raise ValueError("The OCSP responder returned an incorrect response")
    nonce = request.extensions.get_extension_for_class(x509.OCSPNonce).value
    if reply.extensions.get_extension_for_class(x509.OCSPNonce).value != nonce:
        raise ValueError("The OCSP responder did not echo the readiness nonce")
    signer.public_key().verify(reply.signature, reply.tbs_response_bytes, padding.PKCS1v15(), reply.signature_hash_algorithm)
    now = datetime.now(timezone.utc)
    this_update, next_update = utc_time(reply, "this_update"), utc_time(reply, "next_update")
    if this_update is None or next_update is None or not this_update <= now < next_update:
        raise ValueError("The OCSP response is not currently valid")


def check_services(directory: Path, host: str = "127.0.0.1") -> None:
    """Verify the running services belong to this PKI, not just an occupied port."""
    issuer = x509.load_pem_x509_certificate((directory / "intermediate.pem").read_bytes())
    signer = x509.load_pem_x509_certificate((directory / "ocsp-responder.pem").read_bytes())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for name in ("intermediate.der", "intermediate.crl"):
        with opener.open(f"http://127.0.0.1:{CRL_PORT}/{name}", timeout=2) as response:
            if response.status != 200 or response.read() != (directory / name).read_bytes():
                raise ValueError(f"The CRL server returned a stale or incorrect {name}")
    crl = x509.load_der_x509_crl((directory / "intermediate.crl").read_bytes())
    _validate_crl(crl, issuer)

    for name, status in (("good-ocsp", ocsp.OCSPCertStatus.GOOD), ("revoked-ocsp", ocsp.OCSPCertStatus.REVOKED)):
        certificate = x509.load_pem_x509_certificate((directory / f"{name}.pem").read_bytes())
        nonce = x509.OCSPNonce(b"niquests-readiness")
        request = (
            ocsp.OCSPRequestBuilder()
            .add_certificate(certificate, issuer, hashes.SHA1())
            .add_extension(nonce, critical=False)
            .build()
        )
        with opener.open(
            urllib.request.Request(
                OCSP_URL,
                data=request.public_bytes(serialization.Encoding.DER),
                headers={"Content-Type": "application/ocsp-request"},
            ),
            timeout=2,
        ) as response:
            if response.status != 200 or response.headers.get_content_type() != "application/ocsp-response":
                raise ValueError("The OCSP responder returned an invalid HTTP response")
            reply = ocsp.load_der_ocsp_response(response.read())
        _validate_ocsp(reply, request, signer, status)

    context = ssl.create_default_context(cafile=str(directory / "root.pem"))
    for name in LEAVES:
        certificate = x509.load_pem_x509_certificate((directory / f"{name}.pem").read_bytes())
        with socket.create_connection((host, 4443), timeout=2) as connection:
            with context.wrap_socket(connection, server_hostname=f"{name}.httpbin.local") as secure:
                if secure.getpeercert(binary_form=True) != certificate.public_bytes(serialization.Encoding.DER):
                    raise ValueError(f"Traefik is serving a stale or incorrect certificate for {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the local Python revocation services and TLS certificates")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--wait", type=float, default=10)
    args = parser.parse_args()
    deadline = time.monotonic() + args.wait
    while True:
        try:
            check_services(args.directory, args.host)
            return
        except (ConnectionRefusedError, URLError) as exc:
            # urlopen wraps socket errors; only a listener that is not up yet is retryable.
            if isinstance(exc, URLError) and not isinstance(exc.reason, ConnectionRefusedError):
                raise
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Local revocation stack failed readiness checks: {exc}") from exc
            time.sleep(0.2)


if __name__ == "__main__":
    main()
