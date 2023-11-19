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
from datetime import timedelta
from http.cookiejar import CookieJar
from threading import RLock
from urllib.parse import urlparse

import wassima

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time

from ._compat import HAS_LEGACY_URLLIB3

if HAS_LEGACY_URLLIB3 is False:
    from urllib3 import ConnectionInfo, HTTPConnectionPool, HTTPSConnectionPool
    from urllib3.backend import HttpVersion, ResponsePromise
    from urllib3.exceptions import ClosedPoolError, ConnectTimeoutError
    from urllib3.exceptions import HTTPError as _HTTPError
    from urllib3.exceptions import InvalidHeader as _InvalidHeader
    from urllib3.exceptions import (
        LocationValueError,
        MaxRetryError,
        NewConnectionError,
        ProtocolError,
    )
    from urllib3.exceptions import ProxyError as _ProxyError
    from urllib3.exceptions import ReadTimeoutError, ResponseError
    from urllib3.exceptions import SSLError as _SSLError
    from urllib3.poolmanager import PoolManager, ProxyManager, proxy_from_url
    from urllib3.response import BaseHTTPResponse
    from urllib3.util import Timeout as TimeoutSauce
    from urllib3.util import parse_url
    from urllib3.util.retry import Retry
else:
    from urllib3_future import ConnectionInfo, HTTPConnectionPool, HTTPSConnectionPool  # type: ignore[assignment]
    from urllib3_future.backend import HttpVersion, ResponsePromise  # type: ignore[assignment]
    from urllib3_future.exceptions import ClosedPoolError, ConnectTimeoutError  # type: ignore[assignment]
    from urllib3_future.exceptions import HTTPError as _HTTPError  # type: ignore[assignment]
    from urllib3_future.exceptions import InvalidHeader as _InvalidHeader  # type: ignore[assignment]
    from urllib3_future.exceptions import (  # type: ignore[assignment]
        LocationValueError,
        MaxRetryError,
        NewConnectionError,
        ProtocolError,
    )
    from urllib3_future.exceptions import ProxyError as _ProxyError  # type: ignore[assignment]
    from urllib3_future.exceptions import ReadTimeoutError, ResponseError  # type: ignore[assignment]
    from urllib3_future.exceptions import SSLError as _SSLError  # type: ignore[assignment]
    from urllib3_future.poolmanager import PoolManager, ProxyManager, proxy_from_url  # type: ignore[assignment]
    from urllib3_future.response import BaseHTTPResponse  # type: ignore[assignment]
    from urllib3_future.util import Timeout as TimeoutSauce  # type: ignore[assignment]
    from urllib3_future.util import parse_url  # type: ignore[assignment]
    from urllib3_future.util.retry import Retry  # type: ignore[assignment]

from ._constant import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES
from ._typing import (
    CacheLayerAltSvcType,
    HookType,
    ProxyType,
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
    MultiplexingError,
    ProxyError,
    ReadTimeout,
    RetryError,
    SSLError,
    TooManyRedirects,
)
from .hooks import dispatch_hook
from .models import PreparedRequest, Response
from .structures import CaseInsensitiveDict
from .utils import (
    get_auth_from_url,
    get_encoding_from_headers,
    prepend_scheme_if_needed,
    select_proxy,
    urldefragauth,
)

try:
    from .extensions._ocsp import verify as ocsp_verify
except ImportError:
    ocsp_verify = None  # type: ignore[assignment]

try:
    if HAS_LEGACY_URLLIB3 is False:
        from urllib3.contrib.socks import SOCKSProxyManager
    else:
        from urllib3_future.contrib.socks import SOCKSProxyManager  # type: ignore
except ImportError:

    def SOCKSProxyManager(*args: typing.Any, **kwargs: typing.Any) -> None:  # type: ignore[no-redef]
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
        multiplexed: bool = False,
    ) -> Response:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. It is also possible to put the certificates (directly) in a string or bytes.
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
        "_disable_http2",
        "_disable_http3",
    ]

    def __init__(
        self,
        pool_connections: int = DEFAULT_POOLSIZE,
        pool_maxsize: int = DEFAULT_POOLSIZE,
        max_retries: RetryType = DEFAULT_RETRIES,
        pool_block: bool = DEFAULT_POOLBLOCK,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        disable_http2: bool = False,
        disable_http3: bool = False,
        max_in_flight_multiplexed: int | None = None,
    ):
        if isinstance(max_retries, bool):
            self.max_retries: RetryType = False
        elif isinstance(max_retries, Retry):
            self.max_retries = max_retries
        else:
            if max_retries < 0:
                raise ValueError(
                    "configured retries count is invalid. you must specify a positive or zero integer value."
                )
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
        self._disable_http2 = disable_http2
        self._disable_http3 = disable_http3

        #: we keep a list of pending (lazy) response
        self._promises: dict[str, Response] = {}
        self._max_in_flight_multiplexed = (
            max_in_flight_multiplexed
            if max_in_flight_multiplexed is not None
            else self._pool_connections * 124
        )
        self._promise_lock = RLock()

        disabled_svn = set()

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
        )

    def __getstate__(self) -> dict[str, typing.Any | None]:
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        disabled_svn = set()

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
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: The SSL certificate to verify.
        """
        if url.lower().startswith("https") and verify:
            cert_loc: str | None = None
            cert_data: str = wassima.generate_ca_bundle()

            if isinstance(verify, str) and "-----BEGIN CERTIFICATE-----" in verify:
                cert_data = verify
                verify = True

            if isinstance(verify, bytes):
                cert_data = verify.decode("utf-8")
            else:
                # Allow self-specified cert location.
                if isinstance(verify, str):
                    cert_loc = verify

                if isinstance(cert_loc, str) and not os.path.exists(cert_loc):
                    raise OSError(
                        f"Could not find a suitable TLS CA certificate bundle, "
                        f"invalid path: {cert_loc}"
                    )

            conn.cert_reqs = "CERT_REQUIRED"

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
            conn.cert_reqs = "CERT_NONE"
            conn.ca_certs = None
            conn.ca_cert_dir = None
            conn.ca_cert_data = None

        if cert:
            if not isinstance(cert, str):
                if "-----BEGIN CERTIFICATE-----" in cert[0]:
                    conn.cert_data = cert[0]
                    conn.key_data = cert[1]
                else:
                    conn.cert_file = cert[0]
                    conn.key_file = cert[1]
                conn.key_password = cert[2] if len(cert) == 3 else None  # type: ignore[misc]
            else:
                if "-----BEGIN CERTIFICATE-----" in cert:
                    conn.cert_data = cert
                else:
                    conn.cert_file = cert
                conn.key_file = None
                conn.key_password = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(
                    f"Could not find the TLS certificate file, "
                    f"invalid path: {conn.cert_file}"
                )
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(
                    f"Could not find the TLS key file, invalid path: {conn.key_file}"
                )

    def build_response(
        self, req: PreparedRequest, resp: BaseHTTPResponse | ResponsePromise
    ) -> Response:
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

    def get_connection(
        self, url: str, proxies: ProxyType | None = None
    ) -> HTTPConnectionPool | HTTPSConnectionPool:
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
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
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
        scheme = urlparse(request.url).scheme

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            proxy_scheme = urlparse(proxy).scheme.lower()
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
        multiplexed: bool = False,
    ) -> Response:
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use. It is also possible to put the certificates
            (directly) in a string or bytes.
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :param on_post_connection: (optional) A callable that contain a single positional argument for newly acquired
            connection. Useful to check acquired connection information.
        :param multiplexed: Determine if request shall be transmitted by leveraging the multiplexed aspect of the protocol
            if available. Return a lazy instance of Response pending its retrieval.
        """

        assert (
            request.url is not None
            and request.headers is not None
            and request.method is not None
        ), "Tried to send a non-initialized PreparedRequest"

        # We enforce a limit to avoid burning out our connection pool.
        if multiplexed:
            self._promise_lock.acquire()

            if len(self._promises) >= self._max_in_flight_multiplexed:
                self._promise_lock.release()
                self.gather()
            else:
                self._promise_lock.release()

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

        chunked = not (
            bool(request.body) is False or "Content-Length" in request.headers
        )

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

        try:
            resp_or_promise = conn.urlopen(  # type: ignore[call-overload]
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
                multiplexed=multiplexed,
            )

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

    def _future_handler(self, response: Response, low_resp: BaseHTTPResponse) -> None:
        stream = typing.cast(
            bool, response._promise.get_parameter("niquests_is_stream")
        )
        start = typing.cast(float, response._promise.get_parameter("niquests_start"))
        hooks = typing.cast(HookType, response._promise.get_parameter("niquests_hooks"))
        session_cookies = typing.cast(
            CookieJar, response._promise.get_parameter("niquests_cookies")
        )
        allow_redirects = typing.cast(
            bool, response._promise.get_parameter("niquests_allow_redirect")
        )
        max_redirect = typing.cast(
            int, response._promise.get_parameter("niquests_max_redirects")
        )
        redirect_count = typing.cast(
            int, response._promise.get_parameter("niquests_redirect_count")
        )
        kwargs = typing.cast(
            typing.MutableMapping[str, typing.Any],
            response._promise.get_parameter("niquests_kwargs"),
        )

        # mark response as "not lazy" anymore by removing ref to "this"/gather.
        del response._gather

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
        response.raw = low_resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, low_resp)
        extract_cookies_to_jar(session_cookies, req, low_resp)

        promise_ctx_backup = {
            k: v
            for k, v in response._promise._parameters.items()
            if k.startswith("niquests_")
        }

        response_promise = response._promise
        del response._promise

        if allow_redirects:
            next_request = response._resolve_redirect(response, req)
            redirect_count += 1

            if redirect_count > max_redirect + 1:
                raise TooManyRedirects(
                    f"Exceeded {max_redirect} redirects", request=next_request
                )

            if next_request:

                def on_post_connection(conn_info: ConnectionInfo) -> None:
                    """This function will be called by urllib3.future just after establishing the connection."""
                    nonlocal next_request, kwargs

                    assert next_request is not None
                    next_request.conn_info = conn_info

                    if (
                        next_request.url
                        and next_request.url.startswith("https://")
                        and ocsp_verify is not None
                        and kwargs["verify"]
                    ):
                        strict_ocsp_enabled: bool = (
                            os.environ.get("NIQUESTS_STRICT_OCSP", "0") != "0"
                        )

                        ocsp_verify(
                            next_request,
                            strict_ocsp_enabled,
                            0.2 if not strict_ocsp_enabled else 1.0,
                            kwargs["proxies"],
                        )

                kwargs["on_post_connection"] = on_post_connection

                next_promise = self.send(next_request, **kwargs)

                next_promise._gather = lambda: self.gather(response)  # type: ignore[arg-type]
                next_promise._resolve_redirect = response._resolve_redirect

                if "niquests_origin_response" not in promise_ctx_backup:
                    promise_ctx_backup["niquests_origin_response"] = response

                promise_ctx_backup["niquests_origin_response"].history.append(
                    next_promise
                )

                promise_ctx_backup["niquests_start"] = preferred_clock()
                promise_ctx_backup["niquests_redirect_count"] = redirect_count

                for k, v in promise_ctx_backup.items():
                    next_promise._promise.set_parameter(k, v)

                del self._promises[response_promise.uid]

                return
        else:
            response._next = response._resolve_redirect(response, req)  # type: ignore[assignment]

        del response._resolve_redirect

        # In case we handled redirects in a multiplexed connection, we shall reorder history
        # and do a swap.
        if "niquests_origin_response" in promise_ctx_backup:
            origin_response: Response = promise_ctx_backup["niquests_origin_response"]
            leaf_response: Response = origin_response.history[-1]

            origin_response.history.pop()

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
            response.content

        del self._promises[response_promise.uid]

    def gather(self, *responses: Response, max_fetch: int | None = None) -> None:
        with self._promise_lock:
            if not self._promises:
                return

            # Either we did not have a list of promises to fulfill...
            if not responses:
                while True:
                    if max_fetch is not None and max_fetch == 0:
                        return

                    low_resp = self.poolmanager.get_response()

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
                        raise MultiplexingError(
                            "Underlying library yield an unexpected response that did not match any of sent request by us"
                        )

                    self._future_handler(response, low_resp)
            else:
                # ...Or we have a list on which we should focus.
                for response in responses:
                    if max_fetch is not None and max_fetch == 0:
                        return

                    req = response.request

                    assert req is not None

                    if not hasattr(response, "_promise"):
                        continue

                    try:
                        low_resp = self.poolmanager.get_response(
                            promise=response._promise
                        )
                    except ValueError:
                        low_resp = None

                    if low_resp is None:
                        raise MultiplexingError(
                            "Underlying library did not recognize our promise when asked to retrieve it. Did you close the session too early?"
                        )

                    if max_fetch is not None:
                        max_fetch -= 1

                    self._future_handler(response, low_resp)

        self._promise_lock.acquire()

        if self._promises:
            self._promise_lock.release()
            self.gather()
        else:
            self._promise_lock.release()
