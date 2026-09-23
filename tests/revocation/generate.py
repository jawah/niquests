from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtendedKeyUsageOID, NameOID

from . import CRL_URL, DIRECTORY, ISSUER_URL, LEAVES, OCSP_URL


def key_usage(
    *, certificate_signing: bool = False, digital_signature: bool = False, key_encipherment: bool = False
) -> x509.KeyUsage:
    return x509.KeyUsage(
        digital_signature=digital_signature,
        content_commitment=False,
        key_encipherment=key_encipherment,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=certificate_signing,
        crl_sign=certificate_signing,
        encipher_only=False,
        decipher_only=False,
    )


def certificate_builder(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: rsa.RSAPublicKey,
    *,
    serial_number: int,
    now: datetime,
) -> x509.CertificateBuilder:
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(serial_number)
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=7))
    )


def write_key(directory: Path, name: str, key: rsa.RSAPrivateKey, *, served_by_traefik: bool = False) -> None:
    path = directory / f"{name}.key"
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o644 if served_by_traefik else 0o600)


def write_certificate(directory: Path, name: str, certificate: x509.Certificate) -> None:
    path = directory / f"{name}.pem"
    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    path.chmod(0o644)


def issue_leaf(
    directory: Path,
    name: str,
    issuer: x509.Certificate,
    issuer_key: rsa.RSAPrivateKey,
    *,
    serial_number: int,
    now: datetime,
    include_ocsp: bool,
) -> x509.Certificate:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{name}.httpbin.local")])
    access_descriptions = [
        x509.AccessDescription(
            AuthorityInformationAccessOID.CA_ISSUERS,
            x509.UniformResourceIdentifier(ISSUER_URL),
        )
    ]
    if include_ocsp:
        access_descriptions.insert(
            0,
            x509.AccessDescription(
                AuthorityInformationAccessOID.OCSP,
                x509.UniformResourceIdentifier(OCSP_URL),
            ),
        )

    builder = (
        certificate_builder(subject, issuer.subject, key.public_key(), serial_number=serial_number, now=now)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(key_usage(digital_signature=True, key_encipherment=True), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(f"{name}.httpbin.local")]), critical=False)
        .add_extension(x509.AuthorityInformationAccess(access_descriptions), critical=False)
    )
    if not include_ocsp:
        builder = builder.add_extension(
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier(CRL_URL)],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            critical=False,
        )

    certificate = builder.sign(issuer_key, hashes.SHA256())
    write_key(directory, name, key, served_by_traefik=True)
    write_certificate(directory, name, certificate)
    fullchain = directory / f"{name}.fullchain.pem"
    fullchain.write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM) + issuer.public_bytes(serialization.Encoding.PEM)
    )
    fullchain.chmod(0o644)
    return certificate


def generate(directory: Path = DIRECTORY) -> None:
    """Write a fresh seven-day test PKI without invoking external programs."""
    directory = Path(directory)
    directory.mkdir(parents=True, mode=0o755, exist_ok=True)
    directory.chmod(0o755)
    now = datetime.now(timezone.utc)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Niquests Test Root CA")])
    root = (
        certificate_builder(root_name, root_name, root_key.public_key(), serial_number=1, now=now)
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(key_usage(certificate_signing=True), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .sign(root_key, hashes.SHA256())
    )
    write_key(directory, "root", root_key)
    write_certificate(directory, "root", root)

    intermediate_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    intermediate_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Niquests Test Intermediate CA")])
    intermediate = (
        certificate_builder(
            intermediate_name,
            root.subject,
            intermediate_key.public_key(),
            serial_number=2,
            now=now,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(key_usage(certificate_signing=True), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(intermediate_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .sign(root_key, hashes.SHA256())
    )
    write_key(directory, "intermediate", intermediate_key)
    write_certificate(directory, "intermediate", intermediate)
    (directory / "intermediate.der").write_bytes(intermediate.public_bytes(serialization.Encoding.DER))
    (directory / "intermediate.der").chmod(0o644)

    revocation_reasons = {
        "revoked-ocsp": x509.ReasonFlags.affiliation_changed,
        "revoked-crl": x509.ReasonFlags.cessation_of_operation,
    }
    revoked_certificates = []
    for serial, name in enumerate(LEAVES, start=1000):
        certificate = issue_leaf(
            directory,
            name,
            intermediate,
            intermediate_key,
            serial_number=serial,
            now=now,
            include_ocsp=name.endswith("-ocsp"),
        )
        if name in revocation_reasons:
            revoked_certificates.append((certificate, revocation_reasons[name]))

    responder_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    responder_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Niquests Test OCSP Responder")])
    responder = (
        certificate_builder(
            responder_name,
            intermediate.subject,
            responder_key.public_key(),
            serial_number=2000,
            now=now,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(key_usage(digital_signature=True), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.OCSP_SIGNING]), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(responder_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(intermediate_key.public_key()), critical=False)
        .sign(intermediate_key, hashes.SHA256())
    )
    write_key(directory, "ocsp-responder", responder_key)
    write_certificate(directory, "ocsp-responder", responder)

    revoked_at = now - timedelta(minutes=1)
    crl_builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(intermediate.subject)
        .last_update(now - timedelta(minutes=1))
        .next_update(now + timedelta(days=7))
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(intermediate_key.public_key()), critical=False)
        .add_extension(x509.CRLNumber(1), critical=False)
    )
    for certificate, reason in revoked_certificates:
        revoked = (
            x509.RevokedCertificateBuilder()
            .serial_number(certificate.serial_number)
            .revocation_date(revoked_at)
            .add_extension(x509.CRLReason(reason), critical=False)
            .build()
        )
        crl_builder = crl_builder.add_revoked_certificate(revoked)
    crl = crl_builder.sign(intermediate_key, hashes.SHA256())
    (directory / "intermediate.crl").write_bytes(crl.public_bytes(serialization.Encoding.DER))
    (directory / "intermediate.crl").chmod(0o644)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the local OCSP and CRL test PKI")
    parser.add_argument("--directory", type=Path, default=DIRECTORY)
    generate(parser.parse_args().directory)


if __name__ == "__main__":
    main()
