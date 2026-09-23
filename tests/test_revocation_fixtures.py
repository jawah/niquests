"""Opt-in smoke tests for the local PKI and responder; run with `nox -s revocation`."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from http.client import HTTPConnection

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import ocsp
from cryptography.x509.oid import AuthorityInformationAccessOID

from .revocation import CRL_URL, ISSUER_URL, LEAVES, OCSP_URL, generate, ocsp_responder, utc_time


@pytest.fixture(scope="module")
def pki(tmp_path_factory):
    directory = tmp_path_factory.mktemp("revocation")
    generate.generate(directory)
    return directory


def certificate(directory, name):
    return x509.load_pem_x509_certificate((directory / f"{name}.pem").read_bytes())


@pytest.fixture(scope="module")
def server(pki):
    with ocsp_responder.create_server(pki) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_leaf_discovery_extensions(pki):
    for name in LEAVES:
        cert = certificate(pki, name)
        assert list(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value) == [
            x509.DNSName(f"{name}.httpbin.local")
        ]
        expected = {AuthorityInformationAccessOID.CA_ISSUERS: ISSUER_URL}
        if name.endswith("-ocsp"):
            expected[AuthorityInformationAccessOID.OCSP] = OCSP_URL
            with pytest.raises(x509.ExtensionNotFound):
                cert.extensions.get_extension_for_class(x509.CRLDistributionPoints)
        else:
            points = cert.extensions.get_extension_for_class(x509.CRLDistributionPoints).value
            assert len(points) == 1
            assert points[0].full_name == [x509.UniformResourceIdentifier(CRL_URL)]
        aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
        assert {entry.access_method: entry.access_location.value for entry in aia} == expected


def test_crl_membership_and_signature(pki):
    crl = x509.load_der_x509_crl((pki / "intermediate.crl").read_bytes())
    issuer = certificate(pki, "intermediate")
    assert crl.issuer == issuer.subject
    assert crl.is_signature_valid(issuer.public_key())
    assert {entry.serial_number: entry.extensions.get_extension_for_class(x509.CRLReason).value.reason for entry in crl} == {
        certificate(pki, "revoked-ocsp").serial_number: x509.ReasonFlags.affiliation_changed,
        certificate(pki, "revoked-crl").serial_number: x509.ReasonFlags.cessation_of_operation,
    }
    assert utc_time(crl, "last_update") <= datetime.now(timezone.utc) < utc_time(crl, "next_update")


@pytest.mark.parametrize(
    "name,status", (("good-ocsp", ocsp.OCSPCertStatus.GOOD), ("revoked-ocsp", ocsp.OCSPCertStatus.REVOKED))
)
def test_ocsp_status_and_signature(server, pki, name, status):
    request = (
        ocsp.OCSPRequestBuilder()
        .add_certificate(certificate(pki, name), certificate(pki, "intermediate"), hashes.SHA1())
        .build()
    )
    connection = HTTPConnection(*server.server_address, timeout=5)
    try:
        connection.request(
            "POST",
            "/",
            body=request.public_bytes(serialization.Encoding.DER),
            headers={"Content-Type": "application/ocsp-request"},
        )
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Type") == "application/ocsp-response"
        reply = ocsp.load_der_ocsp_response(response.read())
    finally:
        connection.close()

    assert reply.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert reply.certificate_status == status
    assert reply.serial_number == request.serial_number
    assert reply.issuer_name_hash == request.issuer_name_hash
    assert reply.issuer_key_hash == request.issuer_key_hash
    signer = certificate(pki, "ocsp-responder")
    assert list(reply.certificates) == [signer]
    signer.public_key().verify(reply.signature, reply.tbs_response_bytes, padding.PKCS1v15(), reply.signature_hash_algorithm)
    assert utc_time(reply, "this_update") <= datetime.now(timezone.utc) < utc_time(reply, "next_update")
    if status == ocsp.OCSPCertStatus.REVOKED:
        crl = x509.load_der_x509_crl((pki / "intermediate.crl").read_bytes())
        revoked = crl.get_revoked_certificate_by_serial_number(request.serial_number)
        assert reply.revocation_reason == revoked.extensions.get_extension_for_class(x509.CRLReason).value.reason
        assert utc_time(reply, "revocation_time") == utc_time(revoked, "revocation_date")
    else:
        assert reply.revocation_reason is None
        assert utc_time(reply, "revocation_time") is None
