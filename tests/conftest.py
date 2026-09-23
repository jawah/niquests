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
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit

import pytest

# Fixture infrastructure is checked explicitly by `nox -s revocation`.
collect_ignore = ["test_revocation_fixtures.py"]
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


def _local_stack_unavailable(reason: str) -> None:
    if os.environ.get("NIQUESTS_REQUIRE_REVOCATION") == "1" or (
        os.environ.get("CI") and os.environ.get("TRAEFIK_HTTPBIN_ENABLE", "true").lower() == "true"
    ):
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def requires_traefik_http() -> None:
    if os.environ.get("TRAEFIK_HTTPBIN_ENABLE", "true").lower() != "true":
        _local_stack_unavailable("Local Traefik HTTP stack is disabled by TRAEFIK_HTTPBIN_ENABLE")

    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    connection = HTTPConnection(host, 8888, timeout=1)
    try:
        connection.request("GET", "/get", headers={"Host": "httpbin.local"})
        response = connection.getresponse()
        if response.status != 200:
            _local_stack_unavailable(f"Local Traefik HTTP endpoint returned status {response.status} on {host}:8888")
        response.read()
    except (OSError, HTTPException) as exc:
        _local_stack_unavailable(f"Local Traefik HTTP endpoint is unavailable on {host}:8888: {exc}")
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
        _local_stack_unavailable(f"Local Traefik TLS artifacts are missing: {', '.join(missing)}; run `nox -s local_server`")

    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    try:
        context = ssl.create_default_context(cafile=str(root_ca))
        with socket.create_connection((host, 4443), timeout=2) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname="httpbin.local"):
                pass
    except (OSError, ssl.SSLError) as exc:
        _local_stack_unavailable(f"Local Traefik TLS endpoint is unavailable or untrusted on {host}:4443: {exc}")


@pytest.fixture(scope="session")
def requires_revocation_stack(request) -> None:
    # Check the optional backend before probing services, including in main CI.
    try:
        import qh3  # noqa: F401
    except ImportError:
        pytest.skip("qh3 unavailable")

    request.getfixturevalue("requires_traefik_http")
    try:
        from tests.revocation.check import check_services
    except ModuleNotFoundError as exc:
        if exc.name != "cryptography":
            raise
        _local_stack_unavailable(f"Local revocation tests require cryptography and qh3: {exc}")

    revocation = Path(__file__).resolve().parents[1] / "traefik" / "revocation"
    host = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
    try:
        check_services(revocation, host)
    except (ConnectionRefusedError, URLError) as exc:
        if isinstance(exc, URLError) and not isinstance(exc.reason, ConnectionRefusedError):
            raise
        _local_stack_unavailable(f"Local revocation service is not listening: {exc}; run `nox -s local_server`")


@pytest.fixture
def revocation_requests(requires_revocation_stack, monkeypatch):
    """Record real OCSP/CRL fetches without replacing the verification backend."""
    from niquests.adapters import AsyncHTTPAdapter, HTTPAdapter
    from tests.revocation import CRL_PORT, OCSP_PORT

    requests = []
    send = HTTPAdapter.send
    async_send = AsyncHTTPAdapter.send

    def record(request):
        url = urlsplit(request.url)
        if url.hostname == "127.0.0.1" and url.port in (OCSP_PORT, CRL_PORT):
            requests.append(request.url)

    def tracked_send(self, request, *args, **kwargs):
        record(request)
        return send(self, request, *args, **kwargs)

    async def tracked_async_send(self, request, *args, **kwargs):
        record(request)
        return await async_send(self, request, *args, **kwargs)

    monkeypatch.setattr(HTTPAdapter, "send", tracked_send)
    monkeypatch.setattr(AsyncHTTPAdapter, "send", tracked_async_send)
    return requests


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
