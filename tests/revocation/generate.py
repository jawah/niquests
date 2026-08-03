from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "traefik" / "revocation"
CONFIG = Path(__file__).with_name("openssl.cnf")


def run(*args: str, env: dict[str, str] | None = None) -> None:
    if env is None:
        env = os.environ.copy()
        env["CERT_DOMAIN"] = "localhost"
    subprocess.run(["openssl", *args], cwd=ROOT, env=env, check=True)


def issue_leaf(name: str, extension: str) -> None:
    env = os.environ.copy()
    env["CERT_DOMAIN"] = f"{name}.httpbin.local"
    key = OUTPUT / f"{name}.key"
    csr = OUTPUT / f"{name}.csr"
    issued = OUTPUT / f"{name}.issued.pem"
    certificate = OUTPUT / f"{name}.pem"
    run("genrsa", "-out", str(key), "2048")
    if extension != "ocsp_signer":
        key.chmod(0o644)
    run("req", "-new", "-key", str(key), "-subj", f"/CN={name}.httpbin.local", "-out", str(csr))
    run(
        "ca",
        "-batch",
        "-config",
        str(CONFIG),
        "-extensions",
        extension,
        "-in",
        str(csr),
        "-out",
        str(issued),
        env=env,
    )
    run("x509", "-in", str(issued), "-out", str(certificate))
    fullchain = OUTPUT / f"{name}.fullchain.pem"
    fullchain.write_bytes(certificate.read_bytes() + (OUTPUT / "intermediate.pem").read_bytes())
    fullchain.chmod(0o644)


def main() -> None:
    if shutil.which("openssl") is None:
        raise RuntimeError("OpenSSL is required for local revocation tests")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "newcerts").mkdir(parents=True)
    OUTPUT.chmod(0o755)
    (OUTPUT / "index.txt").write_text("")
    (OUTPUT / "serial").write_text("1000\n")
    (OUTPUT / "crlnumber").write_text("1000\n")

    run("genrsa", "-out", str(OUTPUT / "root.key"), "2048")
    run(
        "req",
        "-x509",
        "-new",
        "-key",
        str(OUTPUT / "root.key"),
        "-sha256",
        "-days",
        "7",
        "-subj",
        "/CN=Niquests Test Root CA",
        "-addext",
        "basicConstraints=critical,CA:TRUE,pathlen:1",
        "-addext",
        "keyUsage=critical,keyCertSign,cRLSign",
        "-out",
        str(OUTPUT / "root.pem"),
    )
    run("genrsa", "-out", str(OUTPUT / "intermediate.key"), "2048")
    run(
        "req",
        "-new",
        "-key",
        str(OUTPUT / "intermediate.key"),
        "-subj",
        "/CN=Niquests Test Intermediate CA",
        "-out",
        str(OUTPUT / "intermediate.csr"),
    )
    run(
        "x509",
        "-req",
        "-in",
        str(OUTPUT / "intermediate.csr"),
        "-CA",
        str(OUTPUT / "root.pem"),
        "-CAkey",
        str(OUTPUT / "root.key"),
        "-CAcreateserial",
        "-days",
        "7",
        "-sha256",
        "-extfile",
        str(CONFIG),
        "-extensions",
        "intermediate_ca",
        "-out",
        str(OUTPUT / "intermediate.pem"),
    )
    run("x509", "-in", str(OUTPUT / "intermediate.pem"), "-outform", "DER", "-out", str(OUTPUT / "intermediate.der"))

    issue_leaf("good-ocsp", "server_ocsp")
    issue_leaf("revoked-ocsp", "server_ocsp")
    issue_leaf("good-crl", "server_crl")
    issue_leaf("revoked-crl", "server_crl")
    issue_leaf("ocsp-responder", "ocsp_signer")
    run("ca", "-batch", "-config", str(CONFIG), "-revoke", str(OUTPUT / "revoked-ocsp.pem"), "-crl_reason", "keyCompromise")
    run("ca", "-batch", "-config", str(CONFIG), "-revoke", str(OUTPUT / "revoked-crl.pem"), "-crl_reason", "keyCompromise")
    run("ca", "-batch", "-config", str(CONFIG), "-gencrl", "-out", str(OUTPUT / "intermediate.crl.pem"))
    run("crl", "-in", str(OUTPUT / "intermediate.crl.pem"), "-outform", "DER", "-out", str(OUTPUT / "intermediate.crl"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        raise
