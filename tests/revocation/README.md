# Local Revocation Fixtures

The test PKI and OCSP responder use Python `cryptography` (39 or newer). No OpenSSL
executable is required. Python's TLS and cryptography libraries may still use OpenSSL
internally; this does not replace Niquests' runtime `qh3` revocation backend.

## Run the Tests

```console
nox -s revocation
```

This session installs the revocation extra, generates a fresh PKI, starts the local
Traefik/go-httpbin stack and Python services, checks readiness, and runs the PKI
fixture smoke tests and strict sync/async OCSP/CRL tests. Missing services or dependencies
fail this session instead of silently skipping it. This is an opt-in development session.

The normal `test-*` sessions and main CI run the Niquests integration tests, starting
with Python 3.7. Fixture smoke tests are excluded from default pytest collection:

```console
nox -s test-3.7 -- tests/test_ocsp.py tests/test_crl.py
```

The fixture tests alone need neither Docker nor external network access:

```console
python -m pytest -q tests/test_revocation_fixtures.py
```

The four smoke cases check OCSP/CRL endpoint separation, signed CRL membership and
reasons, and signed GOOD/REVOKED OCSP replies using a temporary PKI and loopback responder.

Live tests repeat requests in the same session and assert that valid and revoked
results are cached: the OCSP or CRL endpoint is contacted only once.
Revoked-certificate tests also check the issuer's reason on both the first request
and the cached failure: `affiliation_changed` for OCSP and `cessation_of_operation`
for CRL. The OCSP responder reads its reason and revocation time from the signed CRL.

## Manual Development

```console
nox -s local_server
```

Leave this command running while testing from another terminal or an IDE with the
development dependencies and `niquests[ocsp]` installed. Ctrl-C stops the host services
and Docker containers. Do not run another managed Nox stack concurrently: the ports
and PKI directory are shared, and occupied revocation ports are rejected.

For Docker-only consumers such as WASI, start a detached stack without host revocation
services:

```console
nox -s local_server -- --no-revocation
docker compose stop
```

The second command stops the containers when finished. Emscripten sessions also run
without host OCSP/CRL services.

## Artifacts and Readiness

- `traefik/revocation/root.pem`: test trust anchor; never install it as a general system CA.
- `http://127.0.0.1:8890/`: OCSP POST endpoint; encoded GET requests are also supported.
- `http://127.0.0.1:8891/intermediate.der`: issuing certificate.
- `http://127.0.0.1:8891/intermediate.crl`: signed DER CRL.
- TLS port `4443`: `good-ocsp`, `revoked-ocsp`, `good-crl`, and `revoked-crl`, each under
  `.httpbin.local`. Nox honors `TRAEFIK_HTTPBIN_IPV4` for the Docker host address.

The OCSP and CRL services always run on host loopback, including when Docker runs
in a separate VM such as Colima on macOS. `TRAEFIK_HTTPBIN_IPV4` only selects the
Docker address; it does not relocate the revocation services.

Managed revocation runs regenerate the seven-day PKI and recreate containers so
Traefik cannot retain an old certificate. Docker-only runs generate missing artifacts
because Traefik's configuration still references those certificates. Stop services
before manually running `python -m tests.revocation.generate`; restart afterward.
The generator also accepts `--directory PATH` for isolated fixture work.

Readiness validates signed GOOD/REVOKED OCSP replies, served issuer/CRL bytes, CRL
signature and validity period, and the exact certificate served by each TLS endpoint.
Only connection refusals are retried during startup. Invalid PKI and responses fail
immediately. Run readiness separately with:

```console
python -m tests.revocation.check --directory traefik/revocation
```

These services and unencrypted keys are only for local testing. Keep other files out
of the generated directory, which the loopback static server exposes. Generated PKI
is ignored by Git. Unknown certificates/issuers receive an unsuccessful UNAUTHORIZED
OCSP response; the fixture responder is not a general-purpose CA service.
