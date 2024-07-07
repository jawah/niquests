from __future__ import annotations

import os
import typing
import warnings
import sys
import time
from http.cookiejar import CookieJar
from collections import OrderedDict
from datetime import timedelta
from urllib.parse import urljoin, urlparse
from .status_codes import codes

if typing.TYPE_CHECKING:
    from typing_extensions import Literal

from ._compat import HAS_LEGACY_URLLIB3, urllib3_ensure_type

if HAS_LEGACY_URLLIB3 is False:
    from urllib3 import ConnectionInfo
    from urllib3.contrib.resolver._async import AsyncBaseResolver
else:
    from urllib3_future import ConnectionInfo  # type: ignore[assignment]
    from urllib3_future.contrib.resolver._async import AsyncBaseResolver  # type: ignore[assignment]

from ._constant import (
    READ_DEFAULT_TIMEOUT,
    WRITE_DEFAULT_TIMEOUT,
    DEFAULT_RETRIES,
    DEFAULT_POOLSIZE,
)
from ._typing import (
    BodyType,
    CookiesType,
    HeadersType,
    HookType,
    HttpAuthenticationType,
    HttpMethodType,
    MultiPartFilesAltType,
    MultiPartFilesType,
    ProxyType,
    QueryParameterType,
    TimeoutType,
    TLSClientCertType,
    TLSVerifyType,
    AsyncResolverType,
    CacheLayerAltSvcType,
    RetryType,
    AsyncHookType,
    AsyncBodyType,
    AsyncHttpAuthenticationType,
)
from .exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    TooManyRedirects,
)
from .hooks import async_dispatch_hook, default_hooks
from .models import (
    PreparedRequest,
    Request,
    Response,
    DEFAULT_REDIRECT_LIMIT,
    TransferProgress,
    AsyncResponse,
)
from .sessions import Session
from .utils import (
    create_async_resolver,
    default_headers,
    resolve_proxies,
    rewind_body,
    requote_uri,
    _swap_context,
    _deepcopy_ci,
    parse_scheme,
    is_ocsp_capable,
)
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    extract_cookies_to_jar,
    merge_cookies,
)
from .structures import AsyncQuicSharedCache
from .adapters import AsyncBaseAdapter, AsyncHTTPAdapter

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time


class AsyncSession(Session):
    """A Requests asynchronous session.

    Provides cookie persistence, connection-pooling, and configuration.

    Basic Usage::

      >>> import niquests
      >>> s = niquests.AsyncSession()
      >>> await s.get('https://httpbin.org/get')
      <Response HTTP/2 [200]>

    Or as a context manager::

      >>> async with niquests.AsyncSession() as s:
      ...     await s.get('https://httpbin.org/get')
      <Response HTTP/2 [200]>
    """

    def __init__(
        self,
        *,
        resolver: AsyncResolverType | None = None,
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
        self.hooks: AsyncHookType[PreparedRequest | Response | AsyncResponse] = (
            default_hooks()  # type: ignore[assignment]
        )

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params: QueryParameterType = {}

        #: Stream response content default.
        self.stream = False

        #: Toggle to leverage multiplexed connection.
        self.multiplexed = multiplexed

        #: Custom DNS resolution method.
        self.resolver: AsyncBaseResolver = create_async_resolver(resolver)
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
        self.cookies: RequestsCookieJar | CookieJar = cookiejar_from_dict(
            {}, thread_free=True
        )

        #: A simple dict that allows us to persist which server support QUIC
        #: It is simply forwarded to urllib3.future that handle the caching logic.
        #: Can be any mutable mapping.
        self.quic_cache_layer = (
            quic_cache_layer
            if quic_cache_layer is not None
            else AsyncQuicSharedCache(max_size=12_288)
        )

        # Default connection adapters.
        self.adapters: OrderedDict[str, AsyncBaseAdapter] = OrderedDict()  # type: ignore[assignment]
        self.mount(
            "https://",
            AsyncHTTPAdapter(
                quic_cache_layer=self.quic_cache_layer,
                max_retries=retries,
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
            AsyncHTTPAdapter(
                max_retries=retries,
                resolver=resolver,
                source_address=source_address,
                disable_ipv4=disable_ipv4,
                disable_ipv6=disable_ipv6,
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                happy_eyeballs=happy_eyeballs,
            ),
        )

    def __enter__(self) -> typing.NoReturn:
        raise SyntaxError(
            'You probably meant "async with". Did you forget to prepend the "async" keyword?'
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, value, tb):
        await self.close()

    def mount(self, prefix: str, adapter: AsyncBaseAdapter) -> None:  # type: ignore[override]
        super().mount(prefix, adapter)  # type: ignore[arg-type]

    def get_adapter(self, url: str) -> AsyncBaseAdapter:  # type: ignore[override]
        return super().get_adapter(url)  # type: ignore[return-value]

    async def send(  # type: ignore[override]
        self, request: PreparedRequest, **kwargs: typing.Any
    ) -> Response | AsyncResponse:  # type: ignore[override]
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
            "timeout" in kwargs
            and kwargs["timeout"]
            and HAS_LEGACY_URLLIB3
            and hasattr(kwargs["timeout"], "total")
            and "urllib3_future" not in str(type(kwargs["timeout"]))
        ):
            kwargs["timeout"] = urllib3_ensure_type(kwargs["timeout"])

        # Set up variables needed for resolve_redirects and dispatching of hooks
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks

        ptr_request = request

        async def on_post_connection(conn_info: ConnectionInfo) -> None:
            """This function will be called by urllib3.future just after establishing the connection."""
            nonlocal ptr_request, request, kwargs
            ptr_request.conn_info = conn_info

            if (
                ptr_request.url
                and ptr_request.url.startswith("https://")
                and kwargs["verify"]
                and is_ocsp_capable(conn_info)
            ):
                strict_ocsp_enabled: bool = (
                    os.environ.get("NIQUESTS_STRICT_OCSP", "0") != "0"
                )

                try:
                    from .extensions._async_ocsp import verify as ocsp_verify
                except ImportError:
                    pass
                else:
                    await ocsp_verify(
                        ptr_request,
                        strict_ocsp_enabled,
                        0.2 if not strict_ocsp_enabled else 1.0,
                        kwargs["proxies"],
                        resolver=self.resolver,
                        happy_eyeballs=self._happy_eyeballs,
                    )

            # don't trigger pre_send for redirects
            if ptr_request == request:
                await async_dispatch_hook("pre_send", hooks, ptr_request)  # type: ignore[arg-type]

        async def handle_upload_progress(
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

            await async_dispatch_hook("on_upload", hooks, request)  # type: ignore[arg-type]

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
                    ResourceWarning,
                )
            await self.close()
            self.resolver = self.resolver.recycle()
            self.mount(
                "https://",
                AsyncHTTPAdapter(
                    quic_cache_layer=self.quic_cache_layer,
                    max_retries=self.retries,
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
                AsyncHTTPAdapter(
                    max_retries=self.retries,
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

        # Send the request
        r = await adapter.send(request, **kwargs)

        # Make sure the timings data are kept as is, conn_info is a reference to
        # urllib3-future conn_info.
        request.conn_info = _deepcopy_ci(request.conn_info)

        # We are leveraging a multiplexed connection
        if r.lazy is True:

            async def _redirect_method_ref(x, y):
                try:
                    return await self.resolve_redirects(
                        x, y, yield_requests=True, **kwargs
                    ).__anext__()
                except StopAsyncIteration:
                    return None

            r._resolve_redirect = _redirect_method_ref

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

            if not stream:
                _swap_context(r)

            return r

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)

        # Response manipulation hooks
        r = await async_dispatch_hook("response", hooks, r, **kwargs)  # type: ignore[arg-type]

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

            async for resp_or_req in gen:
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
            for hr in history:
                if isinstance(hr, AsyncResponse):
                    _swap_context(hr)
            r.history = history  # type: ignore[assignment]

        # If redirects aren't being followed, store the response on the Request for Response.next().
        if not allow_redirects:
            if r.is_redirect:
                try:
                    gen = self.resolve_redirects(
                        r, request, yield_requests=True, **kwargs
                    )
                    r._next = await gen.__anext__()  # type: ignore[assignment]
                except StopAsyncIteration:
                    pass

        if not stream:
            if isinstance(r, AsyncResponse):
                await r.content
                _swap_context(r)
            else:
                r.content

        return r

    async def resolve_redirects(  # type: ignore[override]
        self,
        resp: AsyncResponse,
        req: PreparedRequest,
        stream: bool = False,
        timeout: int | float | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        yield_requests: bool = False,
        yield_requests_trail: bool = False,
        **adapter_kwargs: typing.Any,
    ) -> typing.AsyncGenerator[AsyncResponse | PreparedRequest, None]:
        """Receives a Response. Returns a generator of Responses or Requests."""

        hist = []  # keep track of history

        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()

            # Update history and keep track of redirects.
            # resp.history must ignore the original request in this loop
            hist.append(resp)
            resp.history = hist[1:]  # type: ignore[assignment]

            assert resp.raw is not None

            try:
                if isinstance(resp, AsyncResponse):
                    await resp.content  # Consume socket so it can be released
                else:
                    resp.content
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                await resp.raw.read(decode_content=False)

            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(
                    f"Exceeded {self.max_redirects} redirects.", response=resp
                )

            # Release the connection back into the pool.
            if isinstance(resp, AsyncResponse):
                await resp.close()
            else:
                resp.close()

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith("//"):
                assert resp.url is not None
                target_scheme = parse_scheme(resp.url)
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

                resp = await self.send(  # type: ignore[assignment]
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
                    await self.gather(resp)

                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

                # extract redirect url, if any, for the next loop
                url = self.get_redirect_target(resp)
                yield resp

    @typing.overload  # type: ignore[override]
    async def request(
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = ...,
        data: BodyType | AsyncBodyType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        stream: Literal[False] = ...,
        verify: TLSVerifyType | None = ...,
        cert: TLSClientCertType | None = ...,
        json: typing.Any | None = ...,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def request(
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = ...,
        data: BodyType | AsyncBodyType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        *,
        stream: Literal[True],
        verify: TLSVerifyType | None = ...,
        cert: TLSClientCertType | None = ...,
        json: typing.Any | None = ...,
    ) -> AsyncResponse: ...

    async def request(  # type: ignore[override]
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = None,
        data: BodyType | AsyncBodyType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        stream: bool = False,
        verify: TLSVerifyType | None = None,
        cert: TLSClientCertType | None = None,
        json: typing.Any | None = None,
    ) -> Response | AsyncResponse:
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

        prep: PreparedRequest = self.prepare_request(req)

        if prep._asynchronous_auth:
            r = await prep._pending_async_auth(prep)
            prep.__dict__.update(r.__dict__)
            prep.prepare_content_length(prep.body)
            del prep._pending_async_auth

        prep = await async_dispatch_hook(
            "pre_request",
            hooks,  # type: ignore[arg-type]
            prep,
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

        return await self.send(prep, **send_kwargs)

    @typing.overload  # type: ignore[override]
    async def get(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def get(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> AsyncResponse: ...

    async def get(  # type: ignore[override]
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def options(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def options(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> AsyncResponse: ...

    async def options(  # type: ignore[override]
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def head(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def head(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> AsyncResponse: ...

    async def head(  # type: ignore[override]
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def post(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        json: typing.Any | None = ...,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def post(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        json: typing.Any | None = ...,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse: ...

    async def post(  # type: ignore[override]
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = None,
        json: typing.Any | None = None,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def put(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def put(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse: ...

    async def put(  # type: ignore[override]
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = None,
        *,
        json: typing.Any | None = None,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def patch(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def patch(
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse: ...

    async def patch(  # type: ignore[override]
        self,
        url: str,
        data: BodyType | AsyncBodyType | None = None,
        *,
        json: typing.Any | None = None,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    @typing.overload  # type: ignore[override]
    async def delete(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> Response: ...

    @typing.overload  # type: ignore[override]
    async def delete(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
        **kwargs: typing.Any,
    ) -> AsyncResponse: ...

    async def delete(  # type: ignore[override]
        self,
        url: str,
        *,
        params: QueryParameterType | None = None,
        headers: HeadersType | None = None,
        cookies: CookiesType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
        allow_redirects: bool = True,
        proxies: ProxyType | None = None,
        hooks: HookType[PreparedRequest | Response] | None = None,
        verify: TLSVerifyType = True,
        stream: bool = False,
        cert: TLSClientCertType | None = None,
        **kwargs: typing.Any,
    ) -> Response | AsyncResponse:
        return await self.request(  # type: ignore[call-overload,misc]
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

    async def gather(self, *responses: Response, max_fetch: int | None = None) -> None:  # type: ignore[override]
        if self.multiplexed is False:
            return

        for adapter in self.adapters.values():
            await adapter.gather(*responses, max_fetch=max_fetch)

    async def close(self) -> None:  # type: ignore[override]
        for v in self.adapters.values():
            await v.close()
        if self._own_resolver:
            await self.resolver.close()
