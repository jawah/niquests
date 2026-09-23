from __future__ import annotations

import argparse
import base64
import binascii
import socket
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote_to_bytes

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import ocsp

from . import OCSP_PORT, utc_time

MAX_REQUEST_SIZE = 16 * 1024


def load_certificate(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())


def create_server(directory: Path, port: int = 0) -> ThreadingHTTPServer:
    """Load one fixture PKI and bind a loopback server; the caller runs/closes it."""
    directory = Path(directory)
    issuer = load_certificate(directory / "intermediate.pem")
    responder = load_certificate(directory / "ocsp-responder.pem")
    responder_key = load_pem_private_key((directory / "ocsp-responder.key").read_bytes(), password=None)
    good = load_certificate(directory / "good-ocsp.pem")
    revoked = load_certificate(directory / "revoked-ocsp.pem")
    crl = x509.load_der_x509_crl((directory / "intermediate.crl").read_bytes())
    revocation = crl.get_revoked_certificate_by_serial_number(revoked.serial_number)
    if revocation is None:
        raise ValueError("The OCSP fixture certificate is missing from the CRL")
    revoked_at = utc_time(revocation, "revocation_date")
    revocation_reason = revocation.extensions.get_extension_for_class(x509.CRLReason).value.reason
    certificates = {
        good.serial_number: (good, ocsp.OCSPCertStatus.GOOD),
        revoked.serial_number: (revoked, ocsp.OCSPCertStatus.REVOKED),
    }

    # A handler class per server keeps separate PKIs independent, even with equal serials.
    class OCSPResponder(BaseHTTPRequestHandler):
        timeout = 2

        def do_GET(self) -> None:
            if len(self.path) > 4 * MAX_REQUEST_SIZE + 1:
                self.send_error(414)
                return
            try:
                data = base64.b64decode(unquote_to_bytes(self.path[1:]), validate=True)
            except binascii.Error:
                self.send_ocsp(ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST))
                return
            if len(data) > MAX_REQUEST_SIZE:
                self.send_error(414)
                return
            self.respond(data)

        def do_POST(self) -> None:
            lengths = self.headers.get_all("Content-Length", [])
            if "Transfer-Encoding" in self.headers:
                self.send_error(400, "Transfer-Encoding is not supported")
                return
            if not lengths:
                self.send_error(411)
                return
            if len(lengths) != 1 or not lengths[0] or any(char not in "0123456789" for char in lengths[0]):
                self.send_error(400, "Invalid Content-Length")
                return
            if len(lengths[0]) > 6 or int(lengths[0]) > MAX_REQUEST_SIZE:
                self.send_error(413)
                return
            length = int(lengths[0])
            try:
                data = self.rfile.read(length)
            except socket.timeout:
                self.send_error(408)
                return
            if len(data) != length:
                self.send_error(400, "Incomplete body")
                return
            self.respond(data)

        def respond(self, data: bytes) -> None:
            try:
                request = ocsp.load_der_ocsp_request(data)
                extensions = request.extensions
                algorithm = request.hash_algorithm
            except (ValueError, UnsupportedAlgorithm, x509.DuplicateExtension):
                self.send_ocsp(ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST))
                return
            if any(ext.critical and not isinstance(ext.value, x509.OCSPNonce) for ext in extensions):
                self.send_ocsp(ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST))
                return

            entry = certificates.get(request.serial_number)
            if entry is None:
                self.send_ocsp(ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED))
                return
            certificate, status = entry
            expected = ocsp.OCSPRequestBuilder().add_certificate(certificate, issuer, algorithm).build()
            if request.issuer_name_hash != expected.issuer_name_hash or request.issuer_key_hash != expected.issuer_key_hash:
                self.send_ocsp(ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED))
                return

            now = datetime.now(timezone.utc)
            is_revoked = status == ocsp.OCSPCertStatus.REVOKED
            builder = (
                ocsp.OCSPResponseBuilder()
                .add_response(
                    cert=certificate,
                    issuer=issuer,
                    algorithm=algorithm,
                    cert_status=status,
                    this_update=now - timedelta(seconds=5),
                    next_update=now + timedelta(minutes=10),
                    revocation_time=revoked_at if is_revoked else None,
                    revocation_reason=revocation_reason if is_revoked else None,
                )
                .responder_id(ocsp.OCSPResponderEncoding.HASH, responder)
                .certificates([responder])
            )
            for extension in extensions:
                if isinstance(extension.value, x509.OCSPNonce):
                    builder = builder.add_extension(extension.value, critical=extension.critical)
            self.send_ocsp(builder.sign(responder_key, hashes.SHA256()))

        def send_ocsp(self, response: ocsp.OCSPResponse) -> None:
            payload = response.public_bytes(serialization.Encoding.DER)
            self.send_response(200)
            self.send_header("Content-Type", "application/ocsp-response")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", port), OCSPResponder)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local OCSP fixture responses")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=OCSP_PORT)
    args = parser.parse_args()

    with create_server(args.directory, args.port) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
