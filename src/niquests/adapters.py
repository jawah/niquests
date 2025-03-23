"""
requests.adapters
~~~~~~~~~~~~~~~~~

This module contains the transport adapters that Requests uses to define
and maintain connections.
"""

from __future__ import annotations

import os.path
import socket  # noqa: F401
import sys
import time
import typing
import warnings
from datetime import timedelta
from http.cookiejar import CookieJar
from threading import RLock

import wassima

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time

from ._compat import urllib3_ensure_type
from ._constant import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES
from ._typing import (
    AsyncResolverType,
    CacheLayerAltSvcType,
    HookType,
    ProxyType,
    ResolverType,
    RetryType,
    TLSClientCertType,
    TLSVerifyType,
)
from .auth import _basic_auth_str
from .cookies import extract_cookies_to_jar
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    InvalidHeader,
    InvalidProxyURL,
    InvalidSchema,
    InvalidURL,
    MissingSchema,
    MultiplexingError,
    ProxyError,
    ReadTimeout,
    RetryError,
    SSLError,
    TooManyRedirects,
)
from .hooks import async_dispatch_hook, dispatch_hook
from .models import AsyncResponse, PreparedRequest, Response
from .packages.urllib3 import (
    AsyncHTTPConnectionPool,
    AsyncHTTPSConnectionPool,
    AsyncPoolManager,
    AsyncProxyManager,
    AsyncResolverDescription,
    BaseHTTPResponse,
    ConnectionInfo,
    HTTPConnectionPool,
    HTTPSConnectionPool,
    HttpVersion,
    PoolManager,
    ProxyManager,
    ResolverDescription,
    ResponsePromise,
    async_proxy_from_url,
    proxy_from_url,
)
from .packages.urllib3 import (
    AsyncHTTPResponse as BaseAsyncHTTPResponse,
)
from .packages.urllib3.contrib.resolver import BaseResolver
from .packages.urllib3.contrib.resolver._async import AsyncBaseResolver
from .packages.urllib3.contrib.webextensions import load_extension
from .packages.urllib3.contrib.webextensions._async import (
    load_extension as async_load_extension,
)
from .packages.urllib3.exceptions import (
    ClosedPoolError,
    ConnectTimeoutError,
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
    ReadTimeoutError,
    ResponseError,
)
from .packages.urllib3.exceptions import (
    HTTPError as _HTTPError,
)
from .packages.urllib3.exceptions import (
    InvalidHeader as _InvalidHeader,
)
from .packages.urllib3.exceptions import (
    ProxyError as _ProxyError,
)
from .packages.urllib3.exceptions import (
    SSLError as _SSLError,
)
from .packages.urllib3.util import (
    Retry,
    parse_url,
)
from .packages.urllib3.util import (
    Timeout as TimeoutSauce,
)
from .structures import CaseInsensitiveDict
from .utils import (
    _deepcopy_ci,
    _swap_context,
    async_wrap_extension_for_http,
    get_auth_from_url,
    get_encoding_from_headers,
    is_ocsp_capable,
    parse_scheme,
    prepend_scheme_if_needed,
    resolve_socket_family,
    select_proxy,
    urldefragauth,
    wrap_extension_for_http,
)

try:
    from .packages.urllib3.contrib.socks import AsyncSOCKSProxyManager, SOCKSProxyManager
except ImportError:

    def SOCKSProxyManager(*args: typing.Any, **kwargs: typing.Any) -> None:  # type: ignore[no-redef]
        raise InvalidSchema("Missing dependencies for SOCKS support.")

    def AsyncSOCKSProxyManager(*args: typing.Any, **kwargs: typing.Any) -> None:  # type: ignore[no-redef]
        raise InvalidSchema("Missing dependencies for SOCKS support.")


class BaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self) -> None:
        super().__init__()

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], None] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], None] | None = None,
        on_early_response: typing.Callable[[Response], None] | None = None,
        multiplexed: bool = False,
    ) -> Response:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :param on_post_connection: (optional) A callable that should be invoked just after the pool mgr picked up a live
            connection. The function is expected to takes one positional argument and return nothing.
        :param multiplexed: Determine if we should leverage multiplexed connection.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Cleans up adapter specific items."""
        raise NotImplementedError

    def gather(self, *responses: Response, max_fetch: int | None = None) -> None:
        """
        Load responses that are still 'lazy'. This method is meant for a multiplexed connection.
        Implementation is not mandatory.

        :param max_fetch: Maximal number of response to be fetched before exiting the loop. By default,
            it waits until all pending (lazy) response are resolved.
        """
        pass


class AsyncBaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self) -> None:
        super().__init__()

    async def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], typing.Awaitable[None]] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None = None,
        on_early_response: typing.Callable[[Response], typing.Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> AsyncResponse:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :param on_post_connection: (optional) A callable that should be invoked just after the pool mgr picked up a live
            connection. The function is expected to takes one positional argument and return nothing.
        :param multiplexed: Determine if we should leverage multiplexed connection.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Cleans up adapter specific items."""
        raise NotImplementedError

    async def gather(self, *responses: Response, max_fetch: int | None = None) -> None:
        """
        Load responses that are still 'lazy'. This method is meant for a multiplexed connection.
        Implementation is not mandatory.

        :param max_fetch: Maximal number of response to be fetched before exiting the loop. By default,
            it waits until all pending (lazy) response are resolved.
        """
        pass


class HTTPAdapter(BaseAdapter):
    """The built-in HTTP Adapter for urllib3.future.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import niquests
      >>> s = niquests.Session()
      >>> a = niquests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    __attrs__ = [
        "max_retries",
        "config",
        "_pool_connections",
        "_pool_maxsize",
        "_pool_block",
        "_quic_cache_layer",
        "_disable_http1",
        "_disable_http2",
        "_disable_http3",
        "_source_address",
        "_disable_ipv4",
        "_disable_ipv6",
        "_happy_eyeballs",
        "_keepalive_delay",
        "_keepalive_idle_window",
    ]

    def __init__(
        self,
        pool_connections: int = DEFAULT_POOLSIZE,
        pool_maxsize: int = DEFAULT_POOLSIZE,
        max_retries: RetryType = DEFAULT_RETRIES,
        pool_block: bool = DEFAULT_POOLBLOCK,
        *,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        disable_http1: bool = False,
        disable_http2: bool = False,
        disable_http3: bool = False,
        max_in_flight_multiplexed: int | None = None,
        resolver: ResolverType | None = None,
        source_address: tuple[str, int] | None = None,
        disable_ipv4: bool = False,
        disable_ipv6: bool = False,
        happy_eyeballs: bool | int = False,
        keepalive_delay: float | int | None = 3600.0,
        keepalive_idle_window: float | int | None = 60.0,
    ):
        if isinstance(max_retries, bool):
            self.max_retries: RetryType = False
        elif hasattr(max_retries, "get_backoff_time"):
            self.max_retries = urllib3_ensure_type(max_retries)  # type: ignore[type-var]
        else:
            if max_retries < 0:
                raise ValueError("configured retries count is invalid. you must specify a positive or zero integer value.")
            self.max_retries = Retry.from_int(max_retries)
            # Kept for backward compatibility.
            if max_retries == 0:
                self.max_retries.read = False
        self.config: typing.MutableMapping[str, typing.Any] = {}
        self.proxy_manager: typing.MutableMapping[str, ProxyManager] = {}

        super().__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block
        self._quic_cache_layer = quic_cache_layer
        self._disable_http1 = disable_http1
        self._disable_http2 = disable_http2
        self._disable_http3 = disable_http3
        self._resolver = resolver
        self._source_address = source_address
        self._disable_ipv4 = disable_ipv4
        self._disable_ipv6 = disable_ipv6
        self._happy_eyeballs = happy_eyeballs
        self._keepalive_delay = keepalive_delay
        self._keepalive_idle_window = keepalive_idle_window

        #: we keep a list of pending (lazy) response
        self._promises: dict[str, Response] = {}
        self._orphaned: list[BaseHTTPResponse] = []
        self._max_in_flight_multiplexed = max_in_flight_multiplexed
        self._promise_lock = RLock()

        disabled_svn = set()

        if disable_http1:
            disabled_svn.add(HttpVersion.h11)
        if disable_http2:
            disabled_svn.add(HttpVersion.h2)
        if disable_http3:
            disabled_svn.add(HttpVersion.h3)

        self.init_poolmanager(
            pool_connections,
            pool_maxsize,
            block=pool_block,
            quic_cache_layer=quic_cache_layer,
            disabled_svn=disabled_svn,
            resolver=resolver,
            source_address=source_address,
            socket_family=resolve_socket_family(disable_ipv4, disable_ipv6),
            happy_eyeballs=happy_eyeballs,
            keepalive_delay=keepalive_delay,
            keepalive_idle_window=keepalive_idle_window,
        )

    def __repr__(self) -> str:
        if self.proxy_manager:
            return f"<HTTPAdapter main({self.poolmanager}) proxy({self.proxy_manager})>"
        return f"<HTTPAdapter {self.poolmanager}>"

    def __getstate__(self) -> dict[str, typing.Any | None]:
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        self._resolver = ResolverDescription.from_url("system://").new()

        disabled_svn = set()

        if self._disable_http1:
            disabled_svn.add(HttpVersion.h11)
        if self._disable_http2:
            disabled_svn.add(HttpVersion.h2)
        if self._disable_http3:
            disabled_svn.add(HttpVersion.h3)

        self.init_poolmanager(
            self._pool_connections,
            self._pool_maxsize,
            block=self._pool_block,
            quic_cache_layer=self._quic_cache_layer,
            disabled_svn=disabled_svn,
            source_address=self._source_address,
            socket_family=resolve_socket_family(self._disable_ipv4, self._disable_ipv6),
            happy_eyeballs=self._happy_eyeballs,
            keepalive_delay=self._keepalive_delay,
            keepalive_idle_window=self._keepalive_idle_window,
        )

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        **pool_kwargs: typing.Any,
    ) -> None:
        """Initializes a urllib3 PoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param quic_cache_layer: Caching mutable mapping to remember QUIC capable endpoint.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self._quic_cache_layer = quic_cache_layer

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            preemptive_quic_cache=quic_cache_layer,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: typing.Any) -> ProxyManager:
        """Return urllib3 ProxyManager for the given proxy.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The proxy to return a urllib3 ProxyManager for.
        :param proxy_kwargs: Extra keyword arguments used to configure the Proxy Manager.
        :returns: ProxyManager
        """
        disabled_svn = set()

        if self._disable_http2:
            disabled_svn.add(HttpVersion.h2)

        if self._source_address and "source_address" not in proxy_kwargs:
            proxy_kwargs["source_address"] = self._source_address

        if proxy in self.proxy_manager:
            manager = self.proxy_manager[proxy]
        elif proxy.lower().startswith("socks"):
            username, password = get_auth_from_url(proxy)
            manager = self.proxy_manager[proxy] = SOCKSProxyManager(  # type: ignore[assignment]
                proxy,
                username=username,
                password=password,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                disabled_svn=disabled_svn,
                resolver=self._resolver,
                happy_eyeballs=self._happy_eyeballs,
                **proxy_kwargs,
            )
        else:
            proxy_headers = self.proxy_headers(proxy)
            manager = self.proxy_manager[proxy] = proxy_from_url(
                proxy,
                proxy_headers=proxy_headers,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                disabled_svn=disabled_svn,
                resolver=self._resolver,
                happy_eyeballs=self._happy_eyeballs,
                **proxy_kwargs,
            )

        return manager

    def cert_verify(
        self,
        conn: HTTPSConnectionPool,
        url: str,
        verify: TLSVerifyType | None,
        cert: TLSClientCertType | None,
    ) -> None:
        """Verify a SSL certificate. This method should not be called from user
        code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param conn: The urllib3 connection object associated with the cert.
        :param url: The requested URL.
        :param verify: Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: The SSL certificate to verify.
        """
        if not parse_scheme(url) == "https":
            return

        need_reboot_conn: bool = False
        verify_witness_bit: bool = getattr(conn, "_niquests_verify", object()) == verify

        if not verify_witness_bit:
            if verify:
                cert_loc: str | None = None
                cert_data: str | None = wassima.generate_ca_bundle()
                assert_fingerprint: str | None = None

                if isinstance(verify, str):
                    if "-----BEGIN CERTIFICATE-----" in verify:
                        cert_data = verify
                        verify = True
                    elif verify.startswith("sha256_") or verify.startswith("sha1_"):
                        if len(verify) in [71, 45]:
                            assert_fingerprint = verify.split("_", 1)[-1]
                            verify = False
                            cert_data = None

                if isinstance(verify, bytes):
                    cert_data = verify.decode("utf-8")
                else:
                    # Allow self-specified cert location.
                    # Plain str path
                    if isinstance(verify, str):
                        cert_loc = verify
                    # or path-like obj, that should have __fspath__
                    elif hasattr(verify, "__fspath__"):
                        cert_loc = verify.__fspath__()

                        if isinstance(cert_loc, bytes):
                            cert_loc = cert_loc.decode()

                    if isinstance(cert_loc, str) and not os.path.exists(cert_loc):
                        raise OSError(f"Could not find a suitable TLS CA certificate bundle, invalid path: {cert_loc}")

                if not assert_fingerprint:
                    if conn.cert_reqs != "CERT_REQUIRED":
                        need_reboot_conn = True

                    conn.cert_reqs = "CERT_REQUIRED"
                else:
                    if conn.cert_reqs != "CERT_NONE":
                        need_reboot_conn = True

                    conn.cert_reqs = "CERT_NONE"

                if cert_data and cert_loc is None:
                    conn.ca_certs = None
                    conn.ca_cert_dir = None
                    conn.ca_cert_data = cert_data
                elif cert_loc:
                    if not os.path.isdir(cert_loc):
                        conn.ca_certs = cert_loc
                    else:
                        conn.ca_cert_dir = cert_loc
                else:
                    conn.assert_fingerprint = assert_fingerprint
            else:
                if conn.cert_reqs != "CERT_NONE":
                    need_reboot_conn = True

                conn.cert_reqs = "CERT_NONE"
                conn.ca_certs = None
                conn.ca_cert_dir = None
                conn.ca_cert_data = None

            setattr(conn, "_niquests_verify", verify)
        if cert:
            if not isinstance(cert, str):
                if "-----BEGIN CERTIFICATE-----" in cert[0]:
                    if conn.cert_data != cert[0] or conn.key_data != cert[1]:
                        need_reboot_conn = True
                    conn.cert_data = cert[0]
                    conn.key_data = cert[1]
                else:
                    if conn.cert_file != cert[0] or conn.key_file != cert[1]:
                        need_reboot_conn = True
                    conn.cert_file = cert[0]
                    conn.key_file = cert[1]

                if len(cert) == 3:
                    cert_pwd = cert[2]  # type: ignore[misc]
                    if conn.key_password != cert_pwd:
                        need_reboot_conn = True

                    conn.key_password = cert_pwd
                else:
                    if conn.key_password is not None:
                        conn.key_password = None
                        need_reboot_conn = True
            else:
                if "-----BEGIN CERTIFICATE-----" in cert:
                    conn.cert_data = cert
                else:
                    conn.cert_file = cert
                conn.key_file = None
                conn.key_password = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(f"Could not find the TLS certificate file, invalid path: {conn.cert_file}")
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(f"Could not find the TLS key file, invalid path: {conn.key_file}")

        if need_reboot_conn:
            if conn.is_idle:
                if conn.pool is not None and conn.pool.qsize():
                    conn.pool.clear()
            else:
                warnings.warn(
                    f"The TLS verification changed for {conn.host} but the connection isn't idle.",
                    UserWarning,
                )

    def build_response(self, req: PreparedRequest, resp: BaseHTTPResponse | ResponsePromise) -> Response:
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response or promise object.
        """
        response = Response()

        if isinstance(resp, ResponsePromise) is False:
            # Fallback to None if there's no status_code, for whatever reason.
            response.status_code = getattr(resp, "status", None)

            # Make headers case-insensitive.
            response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))

            # Set encoding.
            response.encoding = get_encoding_from_headers(response.headers)
            response.raw = resp  # type: ignore[assignment]
            response.reason = response.raw.reason  # type: ignore[union-attr]

            if isinstance(req.url, bytes):
                response.url = req.url.decode("utf-8")
            else:
                response.url = req.url

            # Add new cookies from the server.
            extract_cookies_to_jar(response.cookies, req, resp)  # type: ignore[arg-type]
        else:
            with self._promise_lock:
                self._promises[resp.uid] = response  # type: ignore[union-attr]

        # Give the Response some context.
        response.request = req
        response.connection = self  # type: ignore[attr-defined]

        if isinstance(resp, ResponsePromise):
            response._promise = resp

        return response

    def get_connection(self, url: str, proxies: ProxyType | None = None) -> HTTPConnectionPool | HTTPSConnectionPool:
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        proxy = select_proxy(url, proxies)

        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL("Please check proxy URL. It is malformed and could be missing the host.")
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            conn = self.poolmanager.connection_from_url(url)

        return conn

    def close(self) -> None:
        """Disposes of any internal state.

        Currently, this closes the PoolManager and any active ProxyManager,
        which closes any pooled connections.
        """
        self.poolmanager.clear()
        for proxy in self.proxy_manager.values():
            proxy.clear()

    def request_url(self, request: PreparedRequest, proxies: ProxyType | None) -> str:
        """Obtain the url to use when making the final request.

        If the message is being sent through a HTTP proxy, the full URL has to
        be used. Otherwise, we should only use the path portion of the URL.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs.
        """
        assert request.url is not None

        proxy = select_proxy(request.url, proxies)
        scheme = parse_scheme(request.url)

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            try:
                proxy_scheme = parse_scheme(proxy)
            except MissingSchema as e:
                raise ProxyError from e
            using_socks_proxy = proxy_scheme.startswith("socks")

        url = request.path_url
        if is_proxied_http_request and not using_socks_proxy:
            url = urldefragauth(request.url)

        return url

    def add_headers(self, request: PreparedRequest, **kwargs):
        """Add any headers needed by the connection. As of v2.0 this does
        nothing by default, but is left for overriding by users that subclass
        the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` to add headers to.
        :param kwargs: The keyword arguments from the call to send().
        """
        pass

    def proxy_headers(self, proxy: str) -> dict[str, str]:
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. This works with urllib3 magic to ensure that they are
        correctly sent to the proxy, rather than in a tunnelled request if
        CONNECT is being used.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        """
        headers = {}
        username, password = get_auth_from_url(proxy)

        if username:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return headers

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], None] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], None] | None = None,
        on_early_response: typing.Callable[[Response], None] | None = None,
        multiplexed: bool = False,
    ) -> Response:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :param on_post_connection: (optional) A callable that contain a single positional argument for newly acquired
            connection. Useful to check acquired connection information.
        :param multiplexed: Determine if request shall be transmitted by leveraging the multiplexed aspect of the protocol
            if available. Return a lazy instance of Response pending its retrieval.
        """

        assert request.url is not None and request.headers is not None and request.method is not None, (
            "Tried to send a non-initialized PreparedRequest"
        )

        # We enforce a limit to avoid burning out our connection pool.
        if multiplexed and self._max_in_flight_multiplexed is not None:
            with self._promise_lock:
                if len(self._promises) >= self._max_in_flight_multiplexed:
                    self.gather()

        try:
            conn = self.get_connection(request.url, proxies)
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        if isinstance(conn, HTTPSConnectionPool):
            self.cert_verify(conn, request.url, verify, cert)

        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (bool(request.body) is False or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                if len(timeout) == 3:
                    connect, read, total = timeout  # type: ignore[assignment]
                else:
                    connect, read = timeout  # type: ignore[assignment]
                    total = None
                timeout = TimeoutSauce(connect=connect, read=read, total=total)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) or (connect, read, total) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        if isinstance(request.body, (list, dict)):
            raise ValueError("Body contains unprepared native list or dict.")

        scheme = parse_scheme(request.url)
        extension = None

        if scheme is not None and scheme not in ("http", "https"):
            if "+" in scheme:
                scheme, implementation = tuple(scheme.split("+", maxsplit=1))
            else:
                implementation = None

            extension = wrap_extension_for_http(load_extension(scheme, implementation=implementation))()

        def early_response_hook(early_response: BaseHTTPResponse) -> None:
            nonlocal on_early_response
            assert on_early_response is not None
            on_early_response(self.build_response(request, early_response))

        try:
            resp_or_promise = conn.urlopen(  # type: ignore[call-overload,misc]
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
                on_post_connection=on_post_connection,
                on_upload_body=on_upload_body,
                on_early_response=early_response_hook if on_early_response is not None else None,
                extension=extension,
                multiplexed=multiplexed,
            )

            # branch for urllib3.future 2.5+ with advanced conn/multiplexing scheduler/mapper. aka. TrafficPolice.
            # we are bypassing the PoolManager.request to directly invoke the concerned HttpPool, so we missed
            # a required call to TrafficPolice::memorize(...).
            proxy = select_proxy(request.url, proxies)

            if proxy is not None:
                self.proxy_manager[proxy].pools.memorize(resp_or_promise, conn)
                self.proxy_manager[proxy].pools.release()
            else:
                self.poolmanager.pools.memorize(resp_or_promise, conn)
                self.poolmanager.pools.release()

        except (ProtocolError, OSError) as err:
            if "illegal header" in str(err).lower():
                raise InvalidHeader(err, request=request)
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # TODO: Remove this in 3.0.0: see #2811
                if not isinstance(e.reason, NewConnectionError):
                    raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            if isinstance(e.reason, _SSLError):
                # This branch is for urllib3 v1.22 and later.
                raise SSLError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                # This branch is for urllib3 versions earlier than v1.22
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            elif isinstance(e, _InvalidHeader):
                raise InvalidHeader(e, request=request)
            else:
                raise

        return self.build_response(request, resp_or_promise)

    def _future_handler(self, response: Response, low_resp: BaseHTTPResponse) -> Response | None:
        stream: bool = response._promise.get_parameter("niquests_is_stream")  # type: ignore[assignment]
        start: float = response._promise.get_parameter("niquests_start")  # type: ignore[assignment]

        hooks: HookType = response._promise.get_parameter("niquests_hooks")  # type: ignore[assignment]
        session_cookies: CookieJar = response._promise.get_parameter("niquests_cookies")  # type: ignore[assignment]
        allow_redirects: bool = response._promise.get_parameter(  # type: ignore[assignment]
            "niquests_allow_redirect"
        )
        max_redirect: int = response._promise.get_parameter("niquests_max_redirects")  # type: ignore[assignment]
        redirect_count: int = response._promise.get_parameter("niquests_redirect_count")  # type: ignore[assignment]
        kwargs: typing.MutableMapping[str, typing.Any] = response._promise.get_parameter("niquests_kwargs")  # type: ignore[assignment]

        # This mark the response as no longer "lazy"
        response.raw = low_resp
        response_promise = response._promise
        del response._promise

        req = response.request
        assert req is not None

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        response.elapsed = timedelta(seconds=elapsed)

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(low_resp, "status", None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(low_resp, "headers", {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, low_resp)
        extract_cookies_to_jar(session_cookies, req, low_resp)

        promise_ctx_backup = {k: v for k, v in response_promise._parameters.items() if k.startswith("niquests_")}

        if allow_redirects:
            next_request = response._resolve_redirect(response, req)
            redirect_count += 1

            if redirect_count > max_redirect + 1:
                raise TooManyRedirects(f"Exceeded {max_redirect} redirects", request=next_request)

            if next_request:
                del self._promises[response_promise.uid]

                def on_post_connection(conn_info: ConnectionInfo) -> None:
                    """This function will be called by urllib3.future just after establishing the connection."""
                    nonlocal next_request, kwargs

                    assert next_request is not None
                    next_request.conn_info = conn_info

                    if (
                        next_request.url
                        and next_request.url.startswith("https://")
                        and kwargs["verify"]
                        and is_ocsp_capable(conn_info)
                    ):
                        strict_ocsp_enabled: bool = os.environ.get("NIQUESTS_STRICT_OCSP", "0") != "0"

                        try:
                            from .extensions._ocsp import verify as ocsp_verify
                        except ImportError:
                            pass
                        else:
                            ocsp_verify(
                                next_request,
                                strict_ocsp_enabled,
                                0.2 if not strict_ocsp_enabled else 1.0,
                                kwargs["proxies"],
                                self._resolver if isinstance(self._resolver, BaseResolver) else None,
                                self._happy_eyeballs,
                            )

                kwargs["on_post_connection"] = on_post_connection

                next_promise = self.send(next_request, **kwargs)

                # warning: next_promise could be a non-promise if the redirect location does not support
                # multiplexing. We'll have to break the 'lazy' aspect.
                if next_promise.lazy is False:
                    raise MultiplexingError(
                        "A multiplexed request led to a non-multiplexed response after a redirect. "
                        "This is currently unsupported. A patch is in the making to support that edge case."
                    )

                next_request.conn_info = _deepcopy_ci(next_request.conn_info)
                next_promise._resolve_redirect = response._resolve_redirect

                if "niquests_origin_response" not in promise_ctx_backup:
                    promise_ctx_backup["niquests_origin_response"] = response

                promise_ctx_backup["niquests_origin_response"].history.append(next_promise)

                promise_ctx_backup["niquests_start"] = preferred_clock()
                promise_ctx_backup["niquests_redirect_count"] = redirect_count

                for k, v in promise_ctx_backup.items():
                    next_promise._promise.set_parameter(k, v)

                return next_promise
        else:
            response._next = response._resolve_redirect(response, req)  # type: ignore[assignment]

        del response._resolve_redirect
        # In case we handled redirects in a multiplexed connection, we shall reorder history
        # and do a swap.
        if "niquests_origin_response" in promise_ctx_backup:
            origin_response: Response = promise_ctx_backup["niquests_origin_response"]
            leaf_response: Response = origin_response.history[-1]

            origin_response.history.pop()

            origin_response._content = False
            origin_response._content_consumed = False

            origin_response.status_code, leaf_response.status_code = (
                leaf_response.status_code,
                origin_response.status_code,
            )
            origin_response.headers, leaf_response.headers = (
                leaf_response.headers,
                origin_response.headers,
            )
            origin_response.encoding, leaf_response.encoding = (
                leaf_response.encoding,
                origin_response.encoding,
            )
            origin_response.raw, leaf_response.raw = (
                leaf_response.raw,
                origin_response.raw,
            )
            origin_response.reason, leaf_response.reason = (
                leaf_response.reason,
                origin_response.reason,
            )
            origin_response.url, leaf_response.url = (
                leaf_response.url,
                origin_response.url,
            )
            origin_response.elapsed, leaf_response.elapsed = (
                leaf_response.elapsed,
                origin_response.elapsed,
            )
            origin_response.request, leaf_response.request = (
                leaf_response.request,
                origin_response.request,
            )

            origin_response.history = [leaf_response] + origin_response.history

        # Response manipulation hooks
        response = dispatch_hook("response", hooks, response, **kwargs)  # type: ignore[arg-type]

        if response.history:
            # If the hooks create history then we want those cookies too
            for sub_resp in response.history:
                extract_cookies_to_jar(session_cookies, sub_resp.request, sub_resp.raw)

        if not stream:
            if response.extension is None:
                response.content

        del self._promises[response_promise.uid]

        return None

    def gather(self, *responses: Response, max_fetch: int | None = None) -> None:
        with self._promise_lock:
            if not self._promises:
                return

            mgrs: list[PoolManager | ProxyManager] = [
                self.poolmanager,
                *[pm for pm in self.proxy_manager.values()],
            ]

            # Either we did not have a list of promises to fulfill...
            if not responses:
                while True:
                    if max_fetch is not None and max_fetch == 0:
                        return

                    low_resp = None

                    if self._orphaned:
                        for orphan in self._orphaned:
                            try:
                                if orphan._fp.from_promise.uid in self._promises:  # type: ignore[union-attr]
                                    low_resp = orphan
                                    break
                            except AttributeError:
                                continue
                        if low_resp is not None:
                            self._orphaned.remove(low_resp)

                    if low_resp is None:
                        try:
                            for src in mgrs:
                                low_resp = src.get_response()
                                if low_resp is not None:
                                    break
                        except (ProtocolError, OSError) as err:
                            raise ConnectionError(err)

                        except MaxRetryError as e:
                            if isinstance(e.reason, ConnectTimeoutError):
                                # TODO: Remove this in 3.0.0: see #2811
                                if not isinstance(e.reason, NewConnectionError):
                                    raise ConnectTimeout(e)

                            if isinstance(e.reason, ResponseError):
                                raise RetryError(e)

                            if isinstance(e.reason, _ProxyError):
                                raise ProxyError(e)

                            if isinstance(e.reason, _SSLError):
                                # This branch is for urllib3 v1.22 and later.
                                raise SSLError(e)

                            raise ConnectionError(e)

                        except _ProxyError as e:
                            raise ProxyError(e)

                        except (_SSLError, _HTTPError) as e:
                            if isinstance(e, _SSLError):
                                # This branch is for urllib3 versions earlier than v1.22
                                raise SSLError(e)
                            elif isinstance(e, ReadTimeoutError):
                                raise ReadTimeout(e)
                            elif isinstance(e, _InvalidHeader):
                                raise InvalidHeader(e)
                            else:
                                raise

                    if low_resp is None:
                        break

                    if max_fetch is not None:
                        max_fetch -= 1

                    assert (
                        low_resp._fp is not None
                        and hasattr(low_resp._fp, "from_promise")
                        and low_resp._fp.from_promise is not None
                    )

                    response = (
                        self._promises[low_resp._fp.from_promise.uid]
                        if low_resp._fp.from_promise.uid in self._promises
                        else None
                    )

                    if response is None:
                        self._orphaned.append(low_resp)
                        continue

                    self._future_handler(response, low_resp)
            else:
                still_redirects = []

                # ...Or we have a list on which we should focus.
                for response in responses:
                    if max_fetch is not None and max_fetch == 0:
                        return

                    req = response.request

                    assert req is not None

                    if not hasattr(response, "_promise"):
                        continue

                    try:
                        for src in mgrs:
                            try:
                                low_resp = src.get_response(promise=response._promise)
                            except ValueError:
                                low_resp = None

                            if low_resp is not None:
                                break
                    except (ProtocolError, OSError) as err:
                        raise ConnectionError(err)

                    except MaxRetryError as e:
                        if isinstance(e.reason, ConnectTimeoutError):
                            # TODO: Remove this in 3.0.0: see #2811
                            if not isinstance(e.reason, NewConnectionError):
                                raise ConnectTimeout(e)

                        if isinstance(e.reason, ResponseError):
                            raise RetryError(e)

                        if isinstance(e.reason, _ProxyError):
                            raise ProxyError(e)

                        if isinstance(e.reason, _SSLError):
                            # This branch is for urllib3 v1.22 and later.
                            raise SSLError(e)

                        raise ConnectionError(e)

                    except _ProxyError as e:
                        raise ProxyError(e)

                    except (_SSLError, _HTTPError) as e:
                        if isinstance(e, _SSLError):
                            # This branch is for urllib3 versions earlier than v1.22
                            raise SSLError(e)
                        elif isinstance(e, ReadTimeoutError):
                            raise ReadTimeout(e)
                        elif isinstance(e, _InvalidHeader):
                            raise InvalidHeader(e)
                        else:
                            raise

                    if low_resp is None:
                        raise MultiplexingError(
                            "Underlying library did not recognize our promise when asked to retrieve it. "
                            "Did you close the session too early?"
                        )

                    if max_fetch is not None:
                        max_fetch -= 1

                    next_resp = self._future_handler(response, low_resp)

                    if next_resp is not None:
                        still_redirects.append(next_resp)

                if still_redirects:
                    self.gather(*still_redirects)

                return

            if not self._promises:
                return

            self.gather()


class AsyncHTTPAdapter(AsyncBaseAdapter):
    """The built-in HTTP Adapter for urllib3.future asynchronous part.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import niquests
      >>> s = niquests.AsyncSession()
      >>> a = niquests.adapters.AsyncHTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    __attrs__ = [
        "max_retries",
        "config",
        "_pool_connections",
        "_pool_maxsize",
        "_pool_block",
        "_quic_cache_layer",
        "_disable_http1",
        "_disable_http2",
        "_disable_http3",
        "_source_address",
        "_disable_ipv4",
        "_disable_ipv6",
        "_happy_eyeballs",
        "_keepalive_delay",
        "_keepalive_idle_window",
    ]

    def __init__(
        self,
        pool_connections: int = DEFAULT_POOLSIZE,
        pool_maxsize: int = DEFAULT_POOLSIZE,
        max_retries: RetryType = DEFAULT_RETRIES,
        pool_block: bool = DEFAULT_POOLBLOCK,
        *,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        disable_http1: bool = False,
        disable_http2: bool = False,
        disable_http3: bool = False,
        max_in_flight_multiplexed: int | None = None,
        resolver: AsyncResolverType | None = None,
        source_address: tuple[str, int] | None = None,
        disable_ipv4: bool = False,
        disable_ipv6: bool = False,
        happy_eyeballs: bool | int = False,
        keepalive_delay: float | int | None = 3600.0,
        keepalive_idle_window: float | int | None = 60.0,
    ):
        if isinstance(max_retries, bool):
            self.max_retries: RetryType = False
        elif hasattr(max_retries, "get_backoff_time"):
            self.max_retries = urllib3_ensure_type(max_retries)  # type: ignore[type-var]
        else:
            if max_retries < 0:
                raise ValueError("configured retries count is invalid. you must specify a positive or zero integer value.")
            self.max_retries = Retry.from_int(max_retries)
            # Kept for backward compatibility.
            if max_retries == 0:
                self.max_retries.read = False

        self.config: typing.MutableMapping[str, typing.Any] = {}
        self.proxy_manager: typing.MutableMapping[str, AsyncProxyManager] = {}

        super().__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block
        self._quic_cache_layer = quic_cache_layer
        self._disable_http1 = disable_http1
        self._disable_http2 = disable_http2
        self._disable_http3 = disable_http3
        self._resolver = resolver
        self._source_address = source_address
        self._disable_ipv4 = disable_ipv4
        self._disable_ipv6 = disable_ipv6
        self._happy_eyeballs = happy_eyeballs
        self._keepalive_delay = keepalive_delay
        self._keepalive_idle_window = keepalive_idle_window

        #: we keep a list of pending (lazy) response
        self._promises: dict[str, Response | AsyncResponse] = {}
        self._orphaned: list[BaseAsyncHTTPResponse] = []
        self._max_in_flight_multiplexed = max_in_flight_multiplexed

        disabled_svn = set()

        if disable_http1:
            disabled_svn.add(HttpVersion.h11)
        if disable_http2:
            disabled_svn.add(HttpVersion.h2)
        if disable_http3:
            disabled_svn.add(HttpVersion.h3)

        self.init_poolmanager(
            pool_connections,
            pool_maxsize,
            block=pool_block,
            quic_cache_layer=quic_cache_layer,
            disabled_svn=disabled_svn,
            resolver=resolver,
            source_address=source_address,
            socket_family=resolve_socket_family(disable_ipv4, disable_ipv6),
            happy_eyeballs=happy_eyeballs,
            keepalive_delay=keepalive_delay,
            keepalive_idle_window=keepalive_idle_window,
        )

    def __repr__(self) -> str:
        if self.proxy_manager:
            return f"<AsyncHTTPAdapter main({self.poolmanager}) proxy({self.proxy_manager})>"
        return f"<AsyncHTTPAdapter {self.poolmanager}>"

    def __getstate__(self) -> dict[str, typing.Any | None]:
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        self._resolver = AsyncResolverDescription.from_url("system://").new()

        disabled_svn = set()

        if self._disable_http1:
            disabled_svn.add(HttpVersion.h11)
        if self._disable_http2:
            disabled_svn.add(HttpVersion.h2)
        if self._disable_http3:
            disabled_svn.add(HttpVersion.h3)

        self.init_poolmanager(
            self._pool_connections,
            self._pool_maxsize,
            block=self._pool_block,
            quic_cache_layer=self._quic_cache_layer,
            disabled_svn=disabled_svn,
            source_address=self._source_address,
            socket_family=resolve_socket_family(self._disable_ipv4, self._disable_ipv6),
            happy_eyeballs=self._happy_eyeballs,
            keepalive_delay=self._keepalive_delay,
            keepalive_idle_window=self._keepalive_idle_window,
        )

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        **pool_kwargs: typing.Any,
    ) -> None:
        """Initializes a urllib3 AsyncPoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.AsyncHTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param quic_cache_layer: Caching mutable mapping to remember QUIC capable endpoint.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self._quic_cache_layer = quic_cache_layer

        self.poolmanager = AsyncPoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            preemptive_quic_cache=quic_cache_layer,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: typing.Any) -> AsyncProxyManager:
        """Return urllib3 AsyncProxyManager for the given proxy.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The proxy to return a urllib3 ProxyManager for.
        :param proxy_kwargs: Extra keyword arguments used to configure the Proxy Manager.
        :returns: ProxyManager
        """
        disabled_svn = set()

        if self._disable_http2:
            disabled_svn.add(HttpVersion.h2)

        if self._source_address and "source_address" not in proxy_kwargs:
            proxy_kwargs["source_address"] = self._source_address

        if proxy in self.proxy_manager:
            manager = self.proxy_manager[proxy]
        elif proxy.lower().startswith("socks"):
            username, password = get_auth_from_url(proxy)
            manager = self.proxy_manager[proxy] = AsyncSOCKSProxyManager(  # type: ignore[assignment]
                proxy,
                username=username,
                password=password,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                disabled_svn=disabled_svn,
                resolver=self._resolver,
                happy_eyeballs=self._happy_eyeballs,
                **proxy_kwargs,
            )
        else:
            proxy_headers = self.proxy_headers(proxy)
            manager = self.proxy_manager[proxy] = async_proxy_from_url(
                proxy,
                proxy_headers=proxy_headers,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                disabled_svn=disabled_svn,
                resolver=self._resolver,
                happy_eyeballs=self._happy_eyeballs,
                **proxy_kwargs,
            )

        return manager

    def cert_verify(
        self,
        conn: AsyncHTTPSConnectionPool,
        url: str,
        verify: TLSVerifyType | None,
        cert: TLSClientCertType | None,
    ) -> bool:
        """Verify a SSL certificate. This method should not be called from user
        code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param conn: The urllib3 connection object associated with the cert.
        :param url: The requested URL.
        :param verify: Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: The SSL certificate to verify.
        """
        if not parse_scheme(url) == "https":
            return False

        need_reboot_conn: bool = False
        verify_witness_bit: bool = getattr(conn, "_niquests_verify", object()) == verify

        if not verify_witness_bit:
            if verify:
                cert_loc: str | None = None
                cert_data: str | None = wassima.generate_ca_bundle()
                assert_fingerprint: str | None = None

                if isinstance(verify, str):
                    if "-----BEGIN CERTIFICATE-----" in verify:
                        cert_data = verify
                        verify = True
                    elif verify.startswith("sha256_") or verify.startswith("sha1_"):
                        if len(verify) in [71, 45]:
                            assert_fingerprint = verify.split("_", 1)[-1]
                            verify = False
                            cert_data = None

                if isinstance(verify, bytes):
                    cert_data = verify.decode("utf-8")
                else:
                    # Allow self-specified cert location.
                    if isinstance(verify, str):
                        cert_loc = verify

                    elif hasattr(verify, "__fspath__"):
                        cert_loc = verify.__fspath__()

                        if isinstance(cert_loc, bytes):
                            cert_loc = cert_loc.decode()

                    if isinstance(cert_loc, str) and not os.path.exists(cert_loc):
                        raise OSError(f"Could not find a suitable TLS CA certificate bundle, invalid path: {cert_loc}")

                if not assert_fingerprint:
                    if conn.cert_reqs != "CERT_REQUIRED":
                        need_reboot_conn = True

                    conn.cert_reqs = "CERT_REQUIRED"
                else:
                    if conn.cert_reqs != "CERT_NONE":
                        need_reboot_conn = True

                    conn.cert_reqs = "CERT_NONE"

                if cert_data and cert_loc is None:
                    conn.ca_certs = None
                    conn.ca_cert_dir = None
                    conn.ca_cert_data = cert_data
                elif cert_loc:
                    if not os.path.isdir(cert_loc):
                        conn.ca_certs = cert_loc
                    else:
                        conn.ca_cert_dir = cert_loc
                else:
                    conn.assert_fingerprint = assert_fingerprint
            else:
                if conn.cert_reqs != "CERT_NONE":
                    need_reboot_conn = True

                conn.cert_reqs = "CERT_NONE"
                conn.ca_certs = None
                conn.ca_cert_dir = None
                conn.ca_cert_data = None

            setattr(conn, "_niquests_verify", verify)

        if cert:
            if not isinstance(cert, str):
                if "-----BEGIN CERTIFICATE-----" in cert[0]:
                    if conn.cert_data != cert[0] or conn.key_data != cert[1]:
                        need_reboot_conn = True
                    conn.cert_data = cert[0]
                    conn.key_data = cert[1]
                else:
                    if conn.cert_file != cert[0] or conn.key_file != cert[1]:
                        need_reboot_conn = True
                    conn.cert_file = cert[0]
                    conn.key_file = cert[1]

                if len(cert) == 3:
                    cert_pwd = cert[2]  # type: ignore[misc]
                    if conn.key_password != cert_pwd:
                        need_reboot_conn = True

                    conn.key_password = cert_pwd
                else:
                    if conn.key_password is not None:
                        conn.key_password = None
                        need_reboot_conn = True
            else:
                if "-----BEGIN CERTIFICATE-----" in cert:
                    conn.cert_data = cert
                else:
                    conn.cert_file = cert
                conn.key_file = None
                conn.key_password = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(f"Could not find the TLS certificate file, invalid path: {conn.cert_file}")
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(f"Could not find the TLS key file, invalid path: {conn.key_file}")

        return need_reboot_conn

    def build_response(self, req: PreparedRequest, resp: BaseAsyncHTTPResponse | ResponsePromise) -> AsyncResponse:
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response or promise object.
        """
        response = AsyncResponse()

        if isinstance(resp, ResponsePromise) is False:
            # Fallback to None if there's no status_code, for whatever reason.
            response.status_code = getattr(resp, "status", None)

            # Make headers case-insensitive.
            response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))

            # Set encoding.
            response.encoding = get_encoding_from_headers(response.headers)
            response.raw = resp  # type: ignore[assignment]
            response.reason = response.raw.reason  # type: ignore[union-attr]

            if isinstance(req.url, bytes):
                response.url = req.url.decode("utf-8")
            else:
                response.url = req.url

            # Add new cookies from the server.
            extract_cookies_to_jar(response.cookies, req, resp)  # type: ignore[arg-type]
        else:
            self._promises[resp.uid] = response  # type: ignore[union-attr]

        # Give the Response some context.
        response.request = req
        response.connection = self  # type: ignore[attr-defined]

        if isinstance(resp, ResponsePromise):
            response._promise = resp

        return response

    async def get_connection(
        self, url: str, proxies: ProxyType | None = None
    ) -> AsyncHTTPConnectionPool | AsyncHTTPSConnectionPool:
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        proxy = select_proxy(url, proxies)

        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL("Please check proxy URL. It is malformed and could be missing the host.")
            proxy_manager = self.proxy_manager_for(proxy)
            conn = await proxy_manager.connection_from_url(url)
        else:
            conn = await self.poolmanager.connection_from_url(url)

        return conn

    async def close(self) -> None:
        """Disposes of any internal state.

        Currently, this closes the PoolManager and any active ProxyManager,
        which closes any pooled connections.
        """
        await self.poolmanager.clear()
        for proxy in self.proxy_manager.values():
            await proxy.clear()

    def request_url(self, request: PreparedRequest, proxies: ProxyType | None) -> str:
        """Obtain the url to use when making the final request.

        If the message is being sent through a HTTP proxy, the full URL has to
        be used. Otherwise, we should only use the path portion of the URL.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs.
        """
        assert request.url is not None

        proxy = select_proxy(request.url, proxies)
        scheme = parse_scheme(request.url)

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            try:
                proxy_scheme = parse_scheme(proxy)
            except MissingSchema as e:
                raise ProxyError from e
            using_socks_proxy = proxy_scheme.startswith("socks")

        url = request.path_url
        if is_proxied_http_request and not using_socks_proxy:
            url = urldefragauth(request.url)

        return url

    def add_headers(self, request: PreparedRequest, **kwargs):
        """Add any headers needed by the connection. As of v2.0 this does
        nothing by default, but is left for overriding by users that subclass
        the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` to add headers to.
        :param kwargs: The keyword arguments from the call to send().
        """
        pass

    def proxy_headers(self, proxy: str) -> dict[str, str]:
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. This works with urllib3 magic to ensure that they are
        correctly sent to the proxy, rather than in a tunnelled request if
        CONNECT is being used.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        """
        headers = {}
        username, password = get_auth_from_url(proxy)

        if username:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return headers

    async def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], typing.Awaitable[None]] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None = None,
        on_early_response: typing.Callable[[Response], typing.Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> AsyncResponse:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :param on_post_connection: (optional) A callable that contain a single positional argument for newly acquired
            connection. Useful to check acquired connection information.
        :param multiplexed: Determine if request shall be transmitted by leveraging the multiplexed aspect of the protocol
            if available. Return a lazy instance of Response pending its retrieval.
        """
        assert request.url is not None and request.headers is not None and request.method is not None, (
            "Tried to send a non-initialized PreparedRequest"
        )

        # We enforce a limit to avoid burning out our connection pool.
        if multiplexed and self._max_in_flight_multiplexed is not None:
            if len(self._promises) >= self._max_in_flight_multiplexed:
                await self.gather()

        try:
            conn = await self.get_connection(request.url, proxies)
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        if isinstance(conn, AsyncHTTPSConnectionPool):
            need_reboot = self.cert_verify(conn, request.url, verify, cert)

            if need_reboot:
                if conn.is_idle:
                    if conn.pool is not None and conn.pool.qsize():
                        await conn.pool.clear()
                else:
                    warnings.warn(
                        f"The TLS verification changed for {conn.host} but the connection isn't idle.",
                        UserWarning,
                    )

        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (bool(request.body) is False or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                if len(timeout) == 3:
                    connect, read, total = timeout  # type: ignore[assignment]
                else:
                    connect, read = timeout  # type: ignore[assignment]
                    total = None
                timeout = TimeoutSauce(connect=connect, read=read, total=total)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) or (connect, read, total) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        if isinstance(request.body, (list, dict)):
            raise ValueError("Body contains unprepared native list or dict.")

        scheme = parse_scheme(request.url)
        extension = None

        if scheme is not None and scheme not in ("http", "https"):
            if "+" in scheme:
                scheme, implementation = tuple(scheme.split("+", maxsplit=1))
            else:
                implementation = None

            extension = async_wrap_extension_for_http(async_load_extension(scheme, implementation=implementation))()

        async def early_response_hook(early_response: BaseAsyncHTTPResponse) -> None:
            nonlocal on_early_response
            assert on_early_response is not None
            await on_early_response(self.build_response(request, early_response))

        try:
            resp_or_promise = await conn.urlopen(  # type: ignore[call-overload,misc]
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
                on_post_connection=on_post_connection,
                on_upload_body=on_upload_body,
                on_early_response=early_response_hook if on_early_response is not None else None,
                extension=extension,
                multiplexed=multiplexed,
            )

            # we are bypassing the PoolManager.request to directly invoke the concerned HttpPool, so we missed
            # a required call to TrafficPolice::memorize(...).
            proxy = select_proxy(request.url, proxies)

            if proxy is not None:
                self.proxy_manager[proxy].pools.memorize(resp_or_promise, conn)
                self.proxy_manager[proxy].pools.release()
            else:
                self.poolmanager.pools.memorize(resp_or_promise, conn)
                self.poolmanager.pools.release()

        except (ProtocolError, OSError) as err:
            if "illegal header" in str(err).lower():
                raise InvalidHeader(err, request=request)
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # TODO: Remove this in 3.0.0: see #2811
                if not isinstance(e.reason, NewConnectionError):
                    raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            if isinstance(e.reason, _SSLError):
                # This branch is for urllib3 v1.22 and later.
                raise SSLError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                # This branch is for urllib3 versions earlier than v1.22
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            elif isinstance(e, _InvalidHeader):
                raise InvalidHeader(e, request=request)
            else:
                raise

        return self.build_response(request, resp_or_promise)

    async def _future_handler(
        self, response: AsyncResponse | Response, low_resp: BaseAsyncHTTPResponse
    ) -> AsyncResponse | None:
        if not isinstance(response, AsyncResponse):
            _swap_context(response)

        assert isinstance(response, AsyncResponse)

        stream: bool = response._promise.get_parameter("niquests_is_stream")  # type: ignore[assignment]
        start: float = response._promise.get_parameter("niquests_start")  # type: ignore[assignment]
        hooks: HookType = response._promise.get_parameter("niquests_hooks")  # type: ignore[assignment]
        session_cookies: CookieJar = response._promise.get_parameter("niquests_cookies")  # type: ignore[assignment]
        allow_redirects: bool = response._promise.get_parameter(  # type: ignore[assignment]
            "niquests_allow_redirect"
        )
        max_redirect: int = response._promise.get_parameter("niquests_max_redirects")  # type: ignore[assignment]
        redirect_count: int = response._promise.get_parameter("niquests_redirect_count")  # type: ignore[assignment]
        kwargs: typing.MutableMapping[str, typing.Any] = response._promise.get_parameter("niquests_kwargs")  # type: ignore[assignment]

        # This mark the response as no longer "lazy"
        response.raw = low_resp
        response_promise = response._promise
        del response._promise

        req = response.request
        assert req is not None

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        response.elapsed = timedelta(seconds=elapsed)

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(low_resp, "status", None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(low_resp, "headers", {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, low_resp)
        extract_cookies_to_jar(session_cookies, req, low_resp)

        promise_ctx_backup = {k: v for k, v in response_promise._parameters.items() if k.startswith("niquests_")}

        if allow_redirects:
            next_request = await response._resolve_redirect(response, req)
            redirect_count += 1

            if redirect_count > max_redirect + 1:
                raise TooManyRedirects(f"Exceeded {max_redirect} redirects", request=next_request)

            if next_request:
                del self._promises[response_promise.uid]

                async def on_post_connection(conn_info: ConnectionInfo) -> None:
                    """This function will be called by urllib3.future just after establishing the connection."""
                    nonlocal next_request, kwargs

                    assert next_request is not None
                    next_request.conn_info = conn_info

                    if (
                        next_request.url
                        and next_request.url.startswith("https://")
                        and kwargs["verify"]
                        and is_ocsp_capable(conn_info)
                    ):
                        try:
                            from .extensions._async_ocsp import (
                                verify as async_ocsp_verify,
                            )
                        except ImportError:
                            pass
                        else:
                            strict_ocsp_enabled: bool = os.environ.get("NIQUESTS_STRICT_OCSP", "0") != "0"

                            await async_ocsp_verify(
                                next_request,
                                strict_ocsp_enabled,
                                0.2 if not strict_ocsp_enabled else 1.0,
                                kwargs["proxies"],
                                self._resolver if isinstance(self._resolver, AsyncBaseResolver) else None,
                                self._happy_eyeballs,
                            )

                kwargs["on_post_connection"] = on_post_connection

                next_promise = await self.send(next_request, **kwargs)

                # warning: next_promise could be a non-promise if the redirect location does not support
                # multiplexing. We'll have to break the 'lazy' aspect.
                if next_promise.lazy is False:
                    raise MultiplexingError(
                        "A multiplexed request led to a non-multiplexed response after a redirect. "
                        "This is currently unsupported. A patch is in the making to support that edge case."
                    )

                next_request.conn_info = _deepcopy_ci(next_request.conn_info)
                next_promise._resolve_redirect = response._resolve_redirect

                if "niquests_origin_response" not in promise_ctx_backup:
                    promise_ctx_backup["niquests_origin_response"] = response

                promise_ctx_backup["niquests_origin_response"].history.append(next_promise)

                promise_ctx_backup["niquests_start"] = preferred_clock()
                promise_ctx_backup["niquests_redirect_count"] = redirect_count

                for k, v in promise_ctx_backup.items():
                    next_promise._promise.set_parameter(k, v)

                return next_promise
        else:
            response._next = await response._resolve_redirect(response, req)  # type: ignore[assignment]

        del response._resolve_redirect
        # In case we handled redirects in a multiplexed connection, we shall reorder history
        # and do a swap.
        if "niquests_origin_response" in promise_ctx_backup:
            origin_response: Response = promise_ctx_backup["niquests_origin_response"]
            leaf_response: Response = origin_response.history[-1]

            origin_response.history.pop()

            origin_response._content = False
            origin_response._content_consumed = False

            origin_response.status_code, leaf_response.status_code = (
                leaf_response.status_code,
                origin_response.status_code,
            )
            origin_response.headers, leaf_response.headers = (
                leaf_response.headers,
                origin_response.headers,
            )
            origin_response.encoding, leaf_response.encoding = (
                leaf_response.encoding,
                origin_response.encoding,
            )
            origin_response.raw, leaf_response.raw = (
                leaf_response.raw,
                origin_response.raw,
            )
            origin_response.reason, leaf_response.reason = (
                leaf_response.reason,
                origin_response.reason,
            )
            origin_response.url, leaf_response.url = (
                leaf_response.url,
                origin_response.url,
            )
            origin_response.elapsed, leaf_response.elapsed = (
                leaf_response.elapsed,
                origin_response.elapsed,
            )
            origin_response.request, leaf_response.request = (
                leaf_response.request,
                origin_response.request,
            )

            origin_response.history = [leaf_response] + origin_response.history

        # Response manipulation hooks
        response = await async_dispatch_hook("response", hooks, response, **kwargs)  # type: ignore[arg-type]

        if response.history:
            # If the hooks create history then we want those cookies too
            for sub_resp in response.history:
                extract_cookies_to_jar(session_cookies, sub_resp.request, sub_resp.raw)

        if not stream:
            if response.extension is None:
                await response.content
            _swap_context(response)

        del self._promises[response_promise.uid]

        return None

    async def gather(self, *responses: Response | AsyncResponse, max_fetch: int | None = None) -> None:
        if not self._promises:
            return

        mgrs: list[AsyncPoolManager | AsyncProxyManager] = [
            self.poolmanager,
            *[pm for pm in self.proxy_manager.values()],
        ]

        # Either we did not have a list of promises to fulfill...
        if not responses:
            while True:
                if max_fetch is not None and max_fetch == 0:
                    return

                low_resp = None

                if self._orphaned:
                    for orphan in self._orphaned:
                        try:
                            if orphan._fp.from_promise.uid in self._promises:  # type: ignore[union-attr]
                                low_resp = orphan
                                break
                        except AttributeError:
                            continue
                    if low_resp is not None:
                        self._orphaned.remove(low_resp)

                if low_resp is None:
                    try:
                        for src in mgrs:
                            low_resp = await src.get_response()
                            if low_resp is not None:
                                break
                    except (ProtocolError, OSError) as err:
                        raise ConnectionError(err)

                    except MaxRetryError as e:
                        if isinstance(e.reason, ConnectTimeoutError):
                            # TODO: Remove this in 3.0.0: see #2811
                            if not isinstance(e.reason, NewConnectionError):
                                raise ConnectTimeout(e)

                        if isinstance(e.reason, ResponseError):
                            raise RetryError(e)

                        if isinstance(e.reason, _ProxyError):
                            raise ProxyError(e)

                        if isinstance(e.reason, _SSLError):
                            # This branch is for urllib3 v1.22 and later.
                            raise SSLError(e)

                        raise ConnectionError(e)

                    except _ProxyError as e:
                        raise ProxyError(e)

                    except (_SSLError, _HTTPError) as e:
                        if isinstance(e, _SSLError):
                            # This branch is for urllib3 versions earlier than v1.22
                            raise SSLError(e)
                        elif isinstance(e, ReadTimeoutError):
                            raise ReadTimeout(e)
                        elif isinstance(e, _InvalidHeader):
                            raise InvalidHeader(e)
                        else:
                            raise

                if low_resp is None:
                    break

                if max_fetch is not None:
                    max_fetch -= 1

                assert (
                    low_resp._fp is not None and hasattr(low_resp._fp, "from_promise") and low_resp._fp.from_promise is not None
                )

                response = (
                    self._promises[low_resp._fp.from_promise.uid] if low_resp._fp.from_promise.uid in self._promises else None
                )

                if response is None:
                    self._orphaned.append(low_resp)
                    continue

                await self._future_handler(response, low_resp)
        else:
            still_redirects = []

            # ...Or we have a list on which we should focus.
            for response in responses:
                if max_fetch is not None and max_fetch == 0:
                    return

                req = response.request

                assert req is not None

                if not hasattr(response, "_promise"):
                    continue

                try:
                    for src in mgrs:
                        try:
                            low_resp = await src.get_response(promise=response._promise)
                        except ValueError:
                            low_resp = None

                        if low_resp is not None:
                            break
                except (ProtocolError, OSError) as err:
                    raise ConnectionError(err)

                except MaxRetryError as e:
                    if isinstance(e.reason, ConnectTimeoutError):
                        # TODO: Remove this in 3.0.0: see #2811
                        if not isinstance(e.reason, NewConnectionError):
                            raise ConnectTimeout(e)

                    if isinstance(e.reason, ResponseError):
                        raise RetryError(e)

                    if isinstance(e.reason, _ProxyError):
                        raise ProxyError(e)

                    if isinstance(e.reason, _SSLError):
                        # This branch is for urllib3 v1.22 and later.
                        raise SSLError(e)

                    raise ConnectionError(e)

                except _ProxyError as e:
                    raise ProxyError(e)

                except (_SSLError, _HTTPError) as e:
                    if isinstance(e, _SSLError):
                        # This branch is for urllib3 versions earlier than v1.22
                        raise SSLError(e)
                    elif isinstance(e, ReadTimeoutError):
                        raise ReadTimeout(e)
                    elif isinstance(e, _InvalidHeader):
                        raise InvalidHeader(e)
                    else:
                        raise

                if low_resp is None:
                    raise MultiplexingError(
                        "Underlying library did not recognize our promise when asked to retrieve it. "
                        "Did you close the session too early?"
                    )

                if max_fetch is not None:
                    max_fetch -= 1

                next_resp = await self._future_handler(response, low_resp)

                if next_resp is not None:
                    still_redirects.append(next_resp)

            if still_redirects:
                await self.gather(*still_redirects)

            return

        if not self._promises:
            return

        await self.gather()
