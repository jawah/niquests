"""
requests.sessions
~~~~~~~~~~~~~~~~~

This module provides a Session object to manage and persist settings across
requests (cookies, auth, proxies).
"""

from __future__ import annotations

import os
import sys
import time
import typing
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from datetime import timedelta
from http import cookiejar as cookielib
from http.cookiejar import CookieJar
from urllib.parse import urljoin, urlparse

from ._compat import HAS_LEGACY_URLLIB3, urllib3_ensure_type

if HAS_LEGACY_URLLIB3 is False:
    from urllib3 import ConnectionInfo
else:
    from urllib3_future import ConnectionInfo  # type: ignore[assignment]

from ._constant import (
    DEFAULT_RETRIES,
    READ_DEFAULT_TIMEOUT,
    WRITE_DEFAULT_TIMEOUT,
    DEFAULT_POOLSIZE,
)
from ._typing import (
    BodyType,
    CacheLayerAltSvcType,
    CookiesType,
    HeadersType,
    HookType,
    HttpAuthenticationType,
    HttpMethodType,
    MultiPartFilesAltType,
    MultiPartFilesType,
    ProxyType,
    QueryParameterType,
    ResolverType,
    RetryType,
    TimeoutType,
    TLSClientCertType,
    TLSVerifyType,
)
from .adapters import BaseAdapter, HTTPAdapter
from .auth import _basic_auth_str
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    extract_cookies_to_jar,
    merge_cookies,
)
from .exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    HTTPError,
    InvalidSchema,
    TooManyRedirects,
)
from .hooks import HOOKS, default_hooks, dispatch_hook

# formerly defined here, reexposed here for backward compatibility
from .models import (  # noqa: F401
    DEFAULT_REDIRECT_LIMIT,
    REDIRECT_STATI,
    PreparedRequest,
    Request,
    Response,
    TransferProgress,
)
from .status_codes import codes
from .structures import CaseInsensitiveDict, QuicSharedCache
from .utils import (  # noqa: F401
    DEFAULT_PORTS,
    default_headers,
    get_auth_from_url,
    get_environ_proxies,
    get_netrc_auth,
    requote_uri,
    resolve_proxies,
    rewind_body,
    should_bypass_proxies,
    to_key_val_list,
    create_resolver,
    _deepcopy_ci,
    parse_scheme,
    is_ocsp_capable,
)

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time


_MSI = typing.TypeVar("_MSI", bound=typing.Mapping)
_MSI_EX = typing.TypeVar("_MSI_EX", typing.Any, None)


def merge_setting(
    request_setting: _MSI | _MSI_EX,
    session_setting: _MSI | _MSI_EX,
    dict_class=OrderedDict,
) -> _MSI | _MSI_EX:
    """Determines appropriate setting for a given request, taking into account
    the explicit setting on that request, and the setting in the session. If a
    setting is a dictionary, they will be merged together using `dict_class`
    """

    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting

    # Bypass if not a dictionary (e.g. verify)
    if isinstance(session_setting, bool) or not (
        isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)
    ):
        return request_setting

    if hasattr(session_setting, "copy"):
        merged_setting = (
            session_setting.copy()
            if session_setting.__class__ is dict_class
            else dict_class(session_setting.copy())
        )
    else:
        merged_setting = dict_class(to_key_val_list(session_setting))

    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for k in merged_setting if merged_setting[k] is None]

    for key in none_keys:
        del merged_setting[key]

    return merged_setting


def merge_hooks(
    request_hooks: HookType,
    session_hooks: HookType,
    dict_class=OrderedDict,
) -> HookType:
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if session_hooks is None:
        return request_hooks

    if request_hooks is None:
        return session_hooks

    tmp_request_hooks: HookType = {}
    tmp_session_hooks: HookType = {}

    for hook_type in HOOKS:
        if len(request_hooks[hook_type]):
            tmp_request_hooks[hook_type] = request_hooks[hook_type]
        if len(session_hooks[hook_type]):
            tmp_session_hooks[hook_type] = session_hooks[hook_type]

    merged_hooks: HookType = merge_setting(
        tmp_request_hooks, tmp_session_hooks, dict_class
    )

    for hook_type in HOOKS:
        if hook_type not in merged_hooks:
            merged_hooks[hook_type] = []

    return merged_hooks


class Session:
    """A Requests session.

    Provides cookie persistence, connection-pooling, and configuration.

    Basic Usage::

      >>> import niquests
      >>> s = niquests.Session()
      >>> s.get('https://httpbin.org/get')
      <Response HTTP/2 [200]>

    Or as a context manager::

      >>> with niquests.Session() as s:
      ...     s.get('https://httpbin.org/get')
      <Response HTTP/2 [200]>
    """

    __attrs__ = [
        "headers",
        "cookies",
        "auth",
        "proxies",
        "hooks",
        "params",
        "verify",
        "cert",
        "stream",
        "trust_env",
        "max_redirects",
        "retries",
        "multiplexed",
        "source_address",
        "_disable_ipv4",
        "_disable_ipv6",
        "_disable_http1",
        "_disable_http2",
        "_disable_http3",
        "_pool_connections",
        "_pool_maxsize",
        "_happy_eyeballs",
    ]

    def __init__(
        self,
        *,
        resolver: ResolverType | None = None,
        source_address: tuple[str, int] | None = None,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        retries: RetryType = DEFAULT_RETRIES,
        multiplexed: bool = False,
        disable_http1: bool = False,
        disable_http2: bool = False,
        disable_http3: bool = False,
        disable_ipv6: bool = False,
        disable_ipv4: bool = False,
        pool_connections: int = DEFAULT_POOLSIZE,
        pool_maxsize: int = DEFAULT_POOLSIZE,
        happy_eyeballs: bool | int = False,
    ):
        """
        :param resolver: Specify a DNS resolver that should be used within this Session.
        :param source_address: Bind Session to a specific network adapter and/or port so that all outgoing requests.
        :param quic_cache_layer: Provide an external cache mechanism to store HTTP/3 host capabilities.
        :param retries: Configure a number of times a request must be automatically retried before giving up.
        :param multiplexed: Enable or disable concurrent request when the remote host support HTTP/2 onward.
        :param disable_http2: Toggle to disable negotiating HTTP/2 with remote peers.
        :param disable_http3: Toggle to disable negotiating HTTP/3 with remote peers.
        :param disable_ipv6: Toggle to disable using IPv6 even if the remote host supports IPv6.
        :param disable_ipv4: Toggle to disable using IPv4 even if the remote host supports IPv4.
        :param pool_connections: Number of concurrent hosts to be handled by this Session at a maximum.
        :param pool_maxsize: Maximum number of concurrent connections per (single) host at a time.
        """
        if [disable_ipv4, disable_ipv6].count(True) == 2:
            raise RuntimeError("Cannot disable both IPv4 and IPv6")

        #: Configured retries for current Session
        self.retries = retries

        if (
            self.retries
            and HAS_LEGACY_URLLIB3
            and hasattr(self.retries, "total")
            and "urllib3_future" not in str(type(self.retries))
        ):
            self.retries = urllib3_ensure_type(self.retries)  # type: ignore[type-var]

        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol or protocol and host to the URL of the proxy
        #: (e.g. {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}) to
        #: be used on each :class:`Request <Request>`.
        self.proxies: ProxyType = {}

        #: Event-handling hooks.
        self.hooks: HookType[PreparedRequest | Response] = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params: QueryParameterType = {}

        #: Stream response content default.
        self.stream = False

        #: Toggle to leverage multiplexed connection.
        self.multiplexed = multiplexed

        #: Custom DNS resolution method.
        self.resolver = create_resolver(resolver)
        #: Internal use, know whether we should/can close it on session close.
        self._own_resolver: bool = resolver != self.resolver

        #: Bind to address/network adapter
        self.source_address = source_address

        self._disable_http1 = disable_http1
        self._disable_http2 = disable_http2
        self._disable_http3 = disable_http3

        self._disable_ipv4 = disable_ipv4
        self._disable_ipv6 = disable_ipv6

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize

        self._happy_eyeballs = happy_eyeballs

        #: SSL Verification default.
        #: Defaults to `True`, requiring requests to verify the TLS certificate at the
        #: remote end.
        #: If verify is set to `False`, requests will accept any TLS certificate
        #: presented by the server, and will ignore hostname mismatches and/or
        #: expired certificates, which will make your application vulnerable to
        #: man-in-the-middle (MitM) attacks.
        #: Only set this to `False` for testing.
        self.verify: TLSVerifyType = True

        #: SSL client certificate default, if String, path to ssl client
        #: cert file (.pem). If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        self.cert: TLSClientCertType | None = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        #: This defaults to requests.models.DEFAULT_REDIRECT_LIMIT, which is
        #: 30.
        self.max_redirects: int = DEFAULT_REDIRECT_LIMIT

        #: Trust environment settings for proxy configuration, default
        #: authentication and similar.
        self.trust_env: bool = True

        #: A CookieJar containing all currently outstanding cookies set on this
        #: session. By default it is a
        #: :class:`RequestsCookieJar <requests.cookies.RequestsCookieJar>`, but
        #: may be any other ``cookielib.CookieJar`` compatible object.
        self.cookies: RequestsCookieJar | CookieJar = cookiejar_from_dict({})

        #: A simple dict that allows us to persist which server support QUIC
        #: It is simply forwarded to urllib3.future that handle the caching logic.
        #: Can be any mutable mapping.
        self.quic_cache_layer = (
            quic_cache_layer
            if quic_cache_layer is not None
            else QuicSharedCache(max_size=12_288)
        )

        # Default connection adapters.
        self.adapters: OrderedDict[str, BaseAdapter] = OrderedDict()
        self.mount(
            "https://",
            HTTPAdapter(
                quic_cache_layer=self.quic_cache_layer,
                max_retries=retries,
                disable_http1=disable_http1,
                disable_http2=disable_http2,
                disable_http3=disable_http3,
                resolver=resolver,
                source_address=source_address,
                disable_ipv4=disable_ipv4,
                disable_ipv6=disable_ipv6,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                happy_eyeballs=happy_eyeballs,
            ),
        )
        self.mount(
            "http://",
            HTTPAdapter(
                max_retries=retries,
                resolver=resolver,
                source_address=source_address,
                disable_http1=disable_http1,
                disable_http2=disable_http2,
                disable_ipv4=disable_ipv4,
                disable_ipv6=disable_ipv6,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                happy_eyeballs=happy_eyeballs,
            ),
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def prepare_request(self, request: Request) -> PreparedRequest:
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for
        transmission and returns it. The :class:`PreparedRequest` has settings
        merged from the :class:`Request <Request>` instance and those of the
        :class:`Session`.

        :param request: :class:`Request` instance to prepare with this
            session's settings.
        """
        cookies = request.cookies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = merge_cookies(
            merge_cookies(RequestsCookieJar(), self.cookies), cookies
        )

        # Set environment's basic authentication if not explicitly set.
        auth = request.auth
        has_authorization_set = (
            "authorization" in self.headers
            or "authorization" in CaseInsensitiveDict(request.headers)
        )

        if self.trust_env and not auth and not self.auth and not has_authorization_set:
            auth = get_netrc_auth(request.url)

        p = PreparedRequest()
        p.prepare(
            method=request.method,
            url=request.url,
            files=request.files,
            data=request.data,
            json=request.json,
            headers=merge_setting(
                request.headers, self.headers, dict_class=CaseInsensitiveDict
            ),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = None,
        data: BodyType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        stream: bool | None = None,
        verify: TLSVerifyType | None = None,
        cert: TLSClientCertType | None = None,
        json: typing.Any | None = None,
    ) -> Response:
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """
        # Kept for BC-purposes. One may use lowercase http verb.
        if method.isupper() is False:
            method = method.upper()

        # Create the Request.
        req = Request(
            method=method,
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )

        prep: PreparedRequest = dispatch_hook(
            "pre_request",
            hooks,  # type: ignore[arg-type]
            self.prepare_request(req),
        )

        assert prep.url is not None

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)

        return resp

    def get(
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response:
        r"""Sends a GET request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
            **kwargs,
        )

    def options(
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response:
        r"""Sends a OPTIONS request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
            **kwargs,
        )

    def head(
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response:
        r"""Sends a HEAD request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to False by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
            **kwargs,
        )

    def post(
        self,
        url: str,
        data: BodyType | None = None,
        json: typing.Any | None = None,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response:
        r"""Sends a POST request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "POST",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
        )

    def put(
        self,
        url: str,
        data: BodyType | None = None,
        *,
        json: typing.Any | None = None,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response:
        r"""Sends a PUT request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "PUT",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
        )

    def patch(
        self,
        url: str,
        data: BodyType | None = None,
        *,
        json: typing.Any | None = None,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response:
        r"""Sends a PATCH request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "PATCH",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
        )

    def delete(
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response:
        r"""Sends a DELETE request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :param allow_redirects: (optional) Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
            It is also possible to put the certificates (directly) in a string or bytes.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
        """

        return self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            verify=verify,
            stream=stream,
            cert=cert,
            **kwargs,
        )

    def send(self, request: PreparedRequest, **kwargs: typing.Any) -> Response:
        """Send a given PreparedRequest."""
        # It's possible that users might accidentally send a Request object.
        # Guard against that specific failure case.
        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")

        # Set defaults that the hooks can utilize to ensure they always have
        # the correct parameters to reproduce the previous request.
        kwargs.setdefault("stream", self.stream)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("cert", self.cert)

        if "proxies" not in kwargs:
            kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)

        if (
            HAS_LEGACY_URLLIB3
            and "timeout" in kwargs
            and kwargs["timeout"]
            and hasattr(kwargs["timeout"], "total")
            and "urllib3_future" not in str(type(kwargs["timeout"]))
        ):
            kwargs["timeout"] = urllib3_ensure_type(kwargs["timeout"])

        # Set up variables needed for resolve_redirects and dispatching of hooks
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks

        ptr_request = request

        def on_post_connection(conn_info: ConnectionInfo) -> None:
            """This function will be called by urllib3.future just after establishing the connection."""
            nonlocal ptr_request, request, kwargs
            ptr_request.conn_info = conn_info

            if (
                ptr_request.url
                and parse_scheme(ptr_request.url) == "https"
                and kwargs["verify"]
                and is_ocsp_capable(conn_info)
            ):
                strict_ocsp_enabled: bool = (
                    os.environ.get("NIQUESTS_STRICT_OCSP", "0") != "0"
                )

                try:
                    from .extensions._ocsp import verify as ocsp_verify
                except ImportError:
                    pass
                else:
                    ocsp_verify(
                        ptr_request,
                        strict_ocsp_enabled,
                        0.2 if not strict_ocsp_enabled else 1.0,
                        kwargs["proxies"],
                        resolver=self.resolver,
                        happy_eyeballs=self._happy_eyeballs,
                    )

            # don't trigger pre_send for redirects
            if ptr_request == request:
                dispatch_hook("pre_send", hooks, ptr_request)  # type: ignore[arg-type]

        def handle_upload_progress(
            total_sent: int,
            content_length: int | None,
            is_completed: bool,
            any_error: bool,
        ) -> None:
            nonlocal ptr_request, request, kwargs
            if ptr_request != request:
                return
            if request.upload_progress is None:
                request.upload_progress = TransferProgress()

            request.upload_progress.total = total_sent
            request.upload_progress.content_length = content_length
            request.upload_progress.is_completed = is_completed
            request.upload_progress.any_error = any_error

            dispatch_hook("on_upload", hooks, request)  # type: ignore[arg-type]

        kwargs.setdefault("on_post_connection", on_post_connection)
        kwargs.setdefault("on_upload_body", handle_upload_progress)
        kwargs.setdefault("multiplexed", self.multiplexed)

        assert request.url is not None

        # Recycle the resolver if unavailable
        if not self.resolver.is_available():
            if not self._own_resolver:
                warnings.warn(
                    "A externally instantiated resolver was closed. Attempt to recycling it internally, "
                    "the Session will detach itself from given resolver.",
                    UserWarning,
                )
            self.close()
            self.resolver = self.resolver.recycle()
            self.mount(
                "https://",
                HTTPAdapter(
                    quic_cache_layer=self.quic_cache_layer,
                    max_retries=self.retries,
                    disable_http1=self._disable_http1,
                    disable_http2=self._disable_http2,
                    disable_http3=self._disable_http3,
                    resolver=self.resolver,
                    source_address=self.source_address,
                    disable_ipv4=self._disable_ipv4,
                    disable_ipv6=self._disable_ipv6,
                    pool_connections=self._pool_connections,
                    pool_maxsize=self._pool_maxsize,
                    happy_eyeballs=self._happy_eyeballs,
                ),
            )
            self.mount(
                "http://",
                HTTPAdapter(
                    max_retries=self.retries,
                    disable_http1=self._disable_http1,
                    disable_http2=self._disable_http2,
                    resolver=self.resolver,
                    source_address=self.source_address,
                    disable_ipv4=self._disable_ipv4,
                    disable_ipv6=self._disable_ipv6,
                    pool_connections=self._pool_connections,
                    pool_maxsize=self._pool_maxsize,
                    happy_eyeballs=self._happy_eyeballs,
                ),
            )

        # Get the appropriate adapter to use
        adapter = self.get_adapter(url=request.url)

        # Start time (approximately) of the request
        start = preferred_clock()

        try:
            # Send the request
            r = adapter.send(request, **kwargs)
        except TypeError:
            # this is required because some people may do an incomplete migration.
            # this will hint them appropriately.
            raise TypeError(
                "You probably tried to add a Requests adapter into a Niquests session. "
                "Make sure you replaced the 'import requests.adapters' into 'import niquests.adapters' "
                "and made required adjustment. If you did this to increase pool_maxsize, know that the "
                "Session constructor support kwargs for it. "
                "See https://niquests.readthedocs.io/en/latest/user/quickstart.html#scale-your-session-pool to learn more."
            )

        # Make sure the timings data are kept as is, conn_info is a reference to
        # urllib3-future conn_info.
        request.conn_info = _deepcopy_ci(request.conn_info)

        # We are leveraging a multiplexed connection
        if r.lazy is True:
            r._resolve_redirect = lambda x, y: next(
                self.resolve_redirects(x, y, yield_requests=True, **kwargs),  # type: ignore
                None,
            )

            # in multiplexed mode, we are unable to forward this local function for safety reasons.
            kwargs["on_post_connection"] = None

            # we intentionally set 'niquests' as the prefix. urllib3.future have its own parameters.
            r._promise.update_parameters(
                {
                    "niquests_is_stream": stream,
                    "niquests_start": start,
                    "niquests_hooks": hooks,
                    "niquests_cookies": self.cookies,
                    "niquests_allow_redirect": allow_redirects,
                    "niquests_kwargs": kwargs,
                    # You may be wondering why we are setting redirect info in promise ctx.
                    # because in multiplexed mode, we are not fully aware of hop/redirect count
                    "niquests_redirect_count": 0,
                    "niquests_max_redirects": self.max_redirects,
                }
            )

            return r

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)

        # Response manipulation hooks
        r = dispatch_hook("response", hooks, r, **kwargs)  # type: ignore[arg-type]

        # Persist cookies
        if r.history:
            # If the hooks create history then we want those cookies too
            for resp in r.history:
                extract_cookies_to_jar(self.cookies, resp.request, resp.raw)

        extract_cookies_to_jar(self.cookies, request, r.raw)

        # Resolve redirects if allowed.
        if allow_redirects:
            # Redirect resolving generator.
            gen = self.resolve_redirects(
                r, request, yield_requests_trail=True, **kwargs
            )
            history = []

            for resp_or_req in gen:
                if isinstance(resp_or_req, Response):
                    history.append(resp_or_req)
                    continue
                ptr_request = resp_or_req
        else:
            history = []

        # Shuffle things around if there's history.
        if history:
            # Insert the first (original) request at the start
            history.insert(0, r)
            # Get the last request made
            r = history.pop()
            r.history = history

        # If redirects aren't being followed, store the response on the Request for Response.next().
        if not allow_redirects:
            if r.is_redirect:
                try:
                    r._next = next(
                        self.resolve_redirects(
                            r, request, yield_requests=True, **kwargs
                        )  # type: ignore[assignment]
                    )
                except StopIteration:
                    pass

        if not stream:
            r.content

        return r

    def gather(self, *responses: Response, max_fetch: int | None = None) -> None:
        """
        Call this method to make sure in-flight responses are retrieved efficiently. This is a no-op
        if multiplexed is set to False (which is the default value). Passing a limited set of responses
        will wait for given promises and discard others for later.

        :param max_fetch: Maximal number of response to be fetched before exiting the loop.
               By default, it waits until all pending (lazy) response are resolved.
        """
        if self.multiplexed is False:
            return

        for adapter in self.adapters.values():
            adapter.gather(*responses, max_fetch=max_fetch)

    def merge_environment_settings(
        self,
        url: str,
        proxies: ProxyType,
        stream: bool | None,
        verify: TLSVerifyType | None,
        cert: TLSClientCertType | None,
    ) -> dict[str, typing.Any]:
        """
        Check the environment and merge it with some settings.
        """
        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            no_proxy = proxies.get("no_proxy") if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            proxies = {**env_proxies, **proxies}

            # Look for requests environment configuration
            # and be compatible with cURL.
            if verify is True or verify is None:
                verify = (
                    os.environ.get("REQUESTS_CA_BUNDLE")
                    or os.environ.get("CURL_CA_BUNDLE")
                    or verify
                )

        # Merge all the kwargs.
        proxies = merge_setting(proxies, self.proxies)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        return {"proxies": proxies, "stream": stream, "verify": verify, "cert": cert}

    def get_adapter(self, url: str) -> BaseAdapter:
        """
        Returns the appropriate connection adapter for the given URL.
        """
        for prefix, adapter in self.adapters.items():
            if url.lower().startswith(prefix.lower()):
                return adapter

        # Nothing matches :-/
        raise InvalidSchema(f"No connection adapters were found for {url!r}")

    def close(self) -> None:
        """Closes all adapters and as such the session"""
        for v in self.adapters.values():
            v.close()
        if self._own_resolver:
            self.resolver.close()

    def mount(self, prefix: str, adapter: BaseAdapter) -> None:
        """Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by prefix length.
        """
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]

        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)

    def __getstate__(self):
        state = {attr: getattr(self, attr, None) for attr in self.__attrs__}
        return state

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)

        self.quic_cache_layer = QuicSharedCache(max_size=12_288)
        self.resolver = create_resolver(None)
        self._own_resolver = True

        self.adapters = OrderedDict()
        self.mount(
            "https://",
            HTTPAdapter(
                quic_cache_layer=self.quic_cache_layer,
                max_retries=self.retries,
                disable_http2=self._disable_http2,
                disable_http3=self._disable_http3,
                source_address=self.source_address,
                disable_ipv4=self._disable_ipv4,
                disable_ipv6=self._disable_ipv6,
                resolver=self.resolver,
                pool_connections=self._pool_connections,
                pool_maxsize=self._pool_maxsize,
                happy_eyeballs=self._happy_eyeballs,
            ),
        )
        self.mount(
            "http://",
            HTTPAdapter(
                max_retries=self.retries,
                source_address=self.source_address,
                disable_ipv4=self._disable_ipv4,
                disable_ipv6=self._disable_ipv6,
                resolver=self.resolver,
                pool_connections=self._pool_connections,
                pool_maxsize=self._pool_maxsize,
                happy_eyeballs=self._happy_eyeballs,
            ),
        )

    def get_redirect_target(self, resp: Response) -> str | None:
        """Receives a Response. Returns a redirect URI or ``None``"""
        # Due to the nature of how requests processes redirects this method will
        # be called at least once upon the original response and at least twice
        # on each subsequent redirect response (if any).
        # If a custom mixin is used to handle this logic, it may be advantageous
        # to cache the redirect location onto the response object as a private
        # attribute.
        if resp.is_redirect:
            location = resp.headers["location"]
            # Currently the underlying http module on py3 decode headers
            # in latin1, but empirical evidence suggests that latin1 is very
            # rarely used with non-ASCII characters in HTTP headers.
            # It is more likely to get UTF8 header rather than latin1.
            # This causes incorrect handling of UTF8 encoded location headers.
            # To solve this, we re-encode the location in latin1.
            try:
                return (
                    location.encode("latin1") if isinstance(location, str) else location
                ).decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return (
                        location.encode("utf-8")
                        if isinstance(location, str)
                        else location
                    ).decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    raise HTTPError(
                        "Response specify a Location header but is unreadable. This is a violation."
                    ) from e
        return None

    def should_strip_auth(self, old_url: str, new_url: str) -> bool:
        """Decide whether Authorization header should be removed when redirecting"""
        old_parsed = urlparse(old_url)
        new_parsed = urlparse(new_url)
        if old_parsed.hostname != new_parsed.hostname:
            return True
        # Special case: allow http -> https redirect when using the standard
        # ports. This isn't specified by RFC 7235, but is kept to avoid
        # breaking backwards compatibility with older versions of requests
        # that allowed any redirects on the same host.
        if (
            old_parsed.scheme == "http"
            and old_parsed.port in (80, None)
            and new_parsed.scheme == "https"
            and new_parsed.port in (443, None)
        ):
            return False

        # Handle default port usage corresponding to scheme.
        changed_port = old_parsed.port != new_parsed.port
        changed_scheme = old_parsed.scheme != new_parsed.scheme
        default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
        if (
            not changed_scheme
            and old_parsed.port in default_port
            and new_parsed.port in default_port
        ):
            return False

        # Standard case: root URI must match
        return changed_port or changed_scheme

    def resolve_redirects(
        self,
        resp: Response,
        req: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        yield_requests: bool = False,
        yield_requests_trail: bool = False,
        **adapter_kwargs: typing.Any,
    ) -> typing.Generator[Response | PreparedRequest, None, None]:
        """Receives a Response. Returns a generator of Responses or Requests."""

        hist = []  # keep track of history

        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()

            # Update history and keep track of redirects.
            # resp.history must ignore the original request in this loop
            hist.append(resp)
            resp.history = hist[1:]

            assert resp.raw is not None

            try:
                resp.content  # Consume socket so it can be released
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                resp.raw.read(decode_content=False)

            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(
                    f"Exceeded {self.max_redirects} redirects.", response=resp
                )

            # Release the connection back into the pool.
            resp.close()

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith("//"):
                parsed_rurl = urlparse(resp.url)
                target_scheme = parsed_rurl.scheme
                if isinstance(target_scheme, bytes):
                    target_scheme = target_scheme.decode()
                url = ":".join([target_scheme, url])

            # Normalize url case and attach previous fragment if needed (RFC 7231 7.1.2)
            parsed = urlparse(url)
            if parsed.fragment == "" and previous_fragment:
                parsed = parsed._replace(
                    fragment=previous_fragment
                    if isinstance(previous_fragment, str)
                    else previous_fragment.decode("utf-8")
                )
            elif parsed.fragment:
                previous_fragment = parsed.fragment
            url = parsed.geturl()

            # Facilitate relative 'location' headers, as allowed by RFC 7231.
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            # Compliant with RFC3986, we percent encode the url.
            if not parsed.netloc:
                url = urljoin(resp.url, requote_uri(url))  # type: ignore[type-var]
                assert isinstance(
                    url, str
                ), f"urljoin produced {type(url)} instead of str"
            else:
                url = requote_uri(url)

            # this shouldn't happen, but kept in extreme case of being nice with BC.
            if isinstance(url, bytes):
                url = url.decode("utf-8")

            prepared_request.url = url
            assert prepared_request.headers is not None

            self.rebuild_method(prepared_request, resp)

            # https://github.com/psf/requests/issues/1084
            if resp.status_code not in (
                codes.temporary_redirect,  # type: ignore[attr-defined]
                codes.permanent_redirect,  # type: ignore[attr-defined]
            ):
                # https://github.com/psf/requests/issues/3490
                purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
                for header in purged_headers:
                    prepared_request.headers.pop(header, None)
                prepared_request.body = None

            headers = prepared_request.headers

            headers.pop("Cookie", None)

            assert prepared_request._cookies is not None
            # Extract any cookies sent on the response to the cookiejar
            # in the new request. Because we've mutated our copied prepared
            # request, use the old one that we haven't yet touched.
            extract_cookies_to_jar(prepared_request._cookies, req, resp.raw)
            merge_cookies(prepared_request._cookies, self.cookies)
            prepared_request.prepare_cookies(prepared_request._cookies)

            # Rebuild auth and proxy information.
            proxies = self.rebuild_proxies(prepared_request, proxies)
            self.rebuild_auth(prepared_request, resp)

            # A failed tell() sets `_body_position` to `object()`. This non-None
            # value ensures `rewindable` will be True, allowing us to raise an
            # UnrewindableBodyError, instead of hanging the connection.
            rewindable = prepared_request._body_position is not None and (
                "Content-Length" in headers or "Transfer-Encoding" in headers
            )

            # Attempt to rewind consumed file-like object.
            if rewindable:
                rewind_body(prepared_request)

            # Override the original request.
            req = prepared_request

            if yield_requests:
                yield req
            else:
                if yield_requests_trail:
                    yield req

                resp = self.send(
                    req,
                    stream=stream,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies,
                    allow_redirects=False,
                    **adapter_kwargs,
                )

                # If the initial request was intended to be lazy but didn't meet required criteria
                # e.g. Setting multiplexed=True, requesting HTTP/1.1 only capable and getting redirected
                # to an HTTP/2+ endpoint.
                if resp.lazy:
                    resp.status_code

                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

                # extract redirect url, if any, for the next loop
                url = self.get_redirect_target(resp)
                yield resp

    def rebuild_auth(
        self, prepared_request: PreparedRequest, response: Response
    ) -> None:
        """When being redirected we may want to strip authentication from the
        request to avoid leaking credentials. This method intelligently removes
        and reapplies authentication where possible to avoid credential loss.
        """
        headers = prepared_request.headers
        url = prepared_request.url

        assert (
            url is not None and headers is not None
        ), "Rebuild auth based on uninitialized PreparedRequest"
        assert (
            response.request and response.request.url
        ), "Rebuild auth based on nonexistent Response->PreparedRequest"

        if "Authorization" in headers and self.should_strip_auth(
            response.request.url, url
        ):
            # If we get redirected to a new host, we should strip out any
            # authentication headers.
            del headers["Authorization"]

        # .netrc might have more auth for us on our new host.
        new_auth = get_netrc_auth(url) if self.trust_env else None
        if new_auth is not None:
            prepared_request.prepare_auth(new_auth)

    def rebuild_proxies(
        self, prepared_request: PreparedRequest, proxies: ProxyType | None
    ) -> ProxyType:
        """This method re-evaluates the proxy configuration by considering the
        environment variables. If we are redirected to a URL covered by
        NO_PROXY, we strip the proxy configuration. Otherwise, we set missing
        proxy keys for this URL (in case they were stripped by a previous
        redirect).

        This method also replaces the Proxy-Authorization header where
        necessary.
        """
        headers = prepared_request.headers
        assert prepared_request.url is not None
        scheme: str = parse_scheme(prepared_request.url)

        assert (
            headers is not None
        ), "Rebuild proxies based on uninitialized PreparedRequest"

        new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)

        if "Proxy-Authorization" in headers:
            del headers["Proxy-Authorization"]

        try:
            username, password = get_auth_from_url(new_proxies[scheme])
        except KeyError:
            username, password = None, None

        # urllib3 handles proxy authorization for us in the standard adapter.
        # Avoid appending this to TLS tunneled requests where it may be leaked.
        if not scheme.startswith("https") and username and password:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return new_proxies

    def rebuild_method(self, prepared_request: PreparedRequest, response: Response):
        """When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = prepared_request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.see_other and method != "HEAD":  # type: ignore[attr-defined]
            method = "GET"

        # Do what the browsers do, despite standards...
        # First, turn 302s into GETs.
        if response.status_code == codes.found and method != "HEAD":  # type: ignore[attr-defined]
            method = "GET"

        # Second, if a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in Issue 1704.
        if response.status_code == codes.moved and method == "POST":  # type: ignore[attr-defined]
            method = "GET"

        prepared_request.method = method
