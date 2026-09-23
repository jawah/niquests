"""Local PKI fixtures shared by the revocation tests and Nox services."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[2] / "traefik" / "revocation"
OCSP_PORT = 8890
CRL_PORT = 8891
OCSP_URL = f"http://127.0.0.1:{OCSP_PORT}/"
ISSUER_URL = f"http://127.0.0.1:{CRL_PORT}/intermediate.der"
CRL_URL = f"http://127.0.0.1:{CRL_PORT}/intermediate.crl"
LEAVES = ("good-ocsp", "revoked-ocsp", "good-crl", "revoked-crl")


def utc_time(value: object, attribute: str) -> datetime | None:
    """Read a UTC timestamp with cryptography 39 and newer."""
    try:
        return getattr(value, f"{attribute}_utc")
    except AttributeError:
        stamp = getattr(value, attribute)
        return stamp.replace(tzinfo=timezone.utc) if stamp is not None else None
