from __future__ import annotations

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

import socket
import ssl
import threading
from urllib.parse import urljoin

import pytest


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
