from __future__ import annotations

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

import os
import socket
import ssl
import threading
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urljoin

import pytest

collect_ignore_glob = ["wasi_guest/**/*.py"]


def prepare_url(value):
    # Issue #1483: Make sure the URL always has a trailing slash
    httpbin_url = value.url.rstrip("/") + "/"

    def inner(*suffix):
        return urljoin(httpbin_url, "/".join(suffix))

    return inner


@pytest.fixture
def httpbin(httpbin):
    return prepare_url(httpbin)


@pytest.fixture
def httpbin_secure(httpbin_secure):
    return prepare_url(httpbin_secure)


class LocalhostCookieTestServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        spot = self.headers.get("Cookie", None)

        self.send_response(204)
        self.send_header("Content-Length", "0")

        if spot is None:
            self.send_header("Set-Cookie", "hello=world; Domain=localhost; Max-Age=120")
        else:
            self.send_header("X-Cookie-Pass", "1" if "hello=world" in spot else "0")

        self.end_headers()


@pytest.fixture
def san_server(tmp_path_factory):
    # delay importing until the fixture in order to make it possible
    # to deselect the test via command-line when trustme is not available
    import trustme

    tmpdir = tmp_path_factory.mktemp("certs")
    ca = trustme.CA()

    server_cert = ca.issue_cert("localhost", common_name="localhost")
    ca_bundle = str(tmpdir / "ca.pem")
    ca.cert_pem.write_to_path(ca_bundle)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_cert.configure_cert(context)
    server = HTTPServer(("localhost", 0), LocalhostCookieTestServer)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    yield "localhost", server.server_address[1], ca_bundle

    server.shutdown()
    server_thread.join()


try:
    from pytest_pyodide.fixture import (
        parse_driver_timeout,
        selenium_common,
        selenium_context_manager,
        selenium_jspi_inner,  # noqa: F401
        set_webdriver_script_timeout,
    )

    @pytest.fixture(scope="module")
    def selenium_jspi_module_scope(request, runtime, web_server_main, playwright_browsers):
        """Module-scoped JSPI Pyodide instance, reused across tests."""
        if runtime in ("firefox", "safari"):
            pytest.skip(f"jspi not supported in {runtime}")
        if request.config.option.runner.lower() == "playwright":
            pytest.skip("jspi not supported with playwright")
        with selenium_common(request, runtime, web_server_main, browsers=playwright_browsers, jspi=True) as selenium:
            yield selenium

    @pytest.fixture
    def selenium_jspi(request, selenium_jspi_module_scope):
        """Function-scoped wrapper that reuses the module-scoped JSPI instance."""
        with selenium_context_manager(selenium_jspi_module_scope) as selenium, set_webdriver_script_timeout(
            selenium, script_timeout=parse_driver_timeout(request.node)
        ):
            yield selenium

except ImportError:
    pass


_WAN_AVAILABLE = None


@pytest.fixture(scope="session")
def requires_traefik_http() -> None:
    if os.environ.get("TRAEFIK_HTTPBIN_ENABLE", "true").lower() != "true":
        pytest.skip("Local Traefik HTTP stack is disabled by TRAEFIK_HTTPBIN_ENABLE")

    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    connection = HTTPConnection(host, 8888, timeout=1)
    try:
        connection.request("GET", "/get", headers={"Host": "httpbin.local"})
        response = connection.getresponse()
        if response.status != 200:
            pytest.skip(f"Local Traefik HTTP endpoint returned status {response.status} on {host}:8888")
        response.read()
    except (OSError, HTTPException) as exc:
        pytest.skip(f"Local Traefik HTTP endpoint is unavailable on {host}:8888: {exc}")
    finally:
        connection.close()


@pytest.fixture(scope="session")
def requires_traefik_tls(requires_traefik_http) -> None:
    root = Path(__file__).resolve().parents[1]
    root_ca = root / "rootCA.pem"
    certificate = root / "traefik" / "httpbin.local.pem"
    private_key = root / "traefik" / "httpbin.local.pem.key"
    missing = [str(path.relative_to(root)) for path in (root_ca, certificate, private_key) if not path.is_file()]
    if missing:
        pytest.skip(f"Local Traefik TLS artifacts are missing: {', '.join(missing)}; run `nox -s local_server`")

    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    try:
        context = ssl.create_default_context(cafile=str(root_ca))
        with socket.create_connection((host, 4443), timeout=2) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname="httpbin.local"):
                pass
    except (OSError, ssl.SSLError) as exc:
        pytest.skip(f"Local Traefik TLS endpoint is unavailable or untrusted on {host}:4443: {exc}")


@pytest.fixture(scope="session")
def requires_revocation_stack(requires_traefik_http) -> None:
    root = Path(__file__).resolve().parents[1]
    revocation = root / "traefik" / "revocation"
    artifacts = (
        "root.pem",
        "intermediate.pem",
        "intermediate.der",
        "intermediate.crl",
        "good-ocsp.fullchain.pem",
        "good-ocsp.key",
        "revoked-ocsp.fullchain.pem",
        "revoked-ocsp.key",
        "good-crl.fullchain.pem",
        "good-crl.key",
        "revoked-crl.fullchain.pem",
        "revoked-crl.key",
        "ocsp-responder.pem",
        "ocsp-responder.key",
        "index.txt",
    )
    missing = [name for name in artifacts if not (revocation / name).is_file()]
    if missing:
        pytest.skip(f"Local revocation PKI artifacts are missing: {', '.join(missing)}; run `nox -s local_server`")

    try:
        with socket.create_connection(("127.0.0.1", 8890), timeout=1) as ocsp_socket:
            ocsp_socket.sendall(b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
            ocsp_socket.shutdown(socket.SHUT_WR)
            ocsp_socket.recv(1)
    except OSError as exc:
        pytest.skip(f"Local OCSP responder is unavailable on 127.0.0.1:8890: {exc}; run `nox -s local_server`")

    crl_connection = HTTPConnection("127.0.0.1", 8891, timeout=1)
    try:
        crl_connection.request("GET", "/intermediate.der")
        response = crl_connection.getresponse()
        if response.status != 200:
            pytest.skip(f"Local CRL server returned status {response.status} on 127.0.0.1:8891")
        response.read()
    except (OSError, HTTPException) as exc:
        pytest.skip(f"Local CRL server is unavailable on 127.0.0.1:8891: {exc}; run `nox -s local_server`")
    finally:
        crl_connection.close()

    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    try:
        context = ssl.create_default_context(cafile=str(revocation / "root.pem"))
        with socket.create_connection((host, 4443), timeout=2) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname="good-ocsp.httpbin.local"):
                pass
    except (OSError, ssl.SSLError) as exc:
        pytest.skip(f"Local revocation TLS endpoint is unavailable or untrusted on {host}:4443: {exc}")


@pytest.fixture(scope="session")
def traefik_ca_bundle(requires_traefik_tls):
    return str(Path(__file__).resolve().parents[1] / "rootCA.pem")


@pytest.fixture(scope="session")
def traefik_resolver():
    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    names = (
        "httpbin.local",
        "alt.httpbin.local",
        "good-ocsp.httpbin.local",
        "revoked-ocsp.httpbin.local",
        "good-crl.httpbin.local",
        "revoked-crl.httpbin.local",
        "127.0.0.1",
    )
    return "in-memory://default?" + "&".join(f"hosts={name}:{host}" for name in names)


@pytest.fixture(scope="session")
def local_httpbin(requires_traefik_http):
    return SimpleNamespace(
        http_url="http://httpbin.local:8888",
        https_url="https://httpbin.local:4443",
        http_alt_url="http://alt.httpbin.local:9999",
        https_alt_url="https://alt.httpbin.local:8754",
        websocket_url="wss://httpbin.local:4443/websocket/echo",
        sse_url="sse://httpbin.local:4443/sse",
    )


@pytest.fixture(scope="session")
def requires_wan() -> None:
    global _WAN_AVAILABLE

    if _WAN_AVAILABLE is not None:
        if _WAN_AVAILABLE is False:
            pytest.skip("Test requires a WAN access to httpbingo.org")
        return

    try:
        sock = socket.create_connection(("httpbingo.org", 443), timeout=1)
    except (ConnectionRefusedError, socket.gaierror, TimeoutError):
        _WAN_AVAILABLE = False
        pytest.skip("Test requires a WAN access to httpbingo.org")
    else:
        _WAN_AVAILABLE = True
        sock.close()
