"""
requests.api
~~~~~~~~~~~~

This module implements the Requests API.

:copyright: (c) 2012 by Kenneth Reitz.
:license: Apache2, see LICENSE for more details.
"""

from __future__ import annotations

import contextvars
import typing

from ._constant import DEFAULT_RETRIES, READ_DEFAULT_TIMEOUT, WRITE_DEFAULT_TIMEOUT
from ._typing import (
    AsyncBodyType,
    AsyncHookType,
    AsyncHttpAuthenticationType,
    BodyType,
    CacheLayerAltSvcType,
    CookiesType,
    HeadersType,
    HttpAuthenticationType,
    HttpMethodType,
    MultiPartFilesAltType,
    MultiPartFilesType,
    ProxyType,
    QueryParameterType,
    RetryType,
    TimeoutType,
    TLSClientCertType,
    TLSVerifyType,
)
from .async_session import AsyncSession
from .models import AsyncResponse, PreparedRequest, Response
from .structures import AsyncQuicSharedCache

try:
    from .extensions._async_ocsp import InMemoryRevocationStatus

    _SHARED_OCSP_CACHE: contextvars.ContextVar[InMemoryRevocationStatus] | None = contextvars.ContextVar(
        "ocsp_cache", default=InMemoryRevocationStatus()
    )
except ImportError:
    _SHARED_OCSP_CACHE = None

_SHARED_QUIC_CACHE: CacheLayerAltSvcType = AsyncQuicSharedCache(max_size=12_288)


@typing.overload
async def request(
    method: HttpMethodType,
    url: str,
    *,
    params: QueryParameterType | None = ...,
    data: BodyType | AsyncBodyType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    stream: typing.Literal[False] | None = ...,
    verify: TLSVerifyType | None = ...,
    cert: TLSClientCertType | None = ...,
    json: typing.Any | None = ...,
    retries: RetryType = ...,
) -> Response: ...


@typing.overload
async def request(
    method: HttpMethodType,
    url: str,
    *,
    params: QueryParameterType | None = ...,
    data: BodyType | AsyncBodyType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    stream: typing.Literal[True] = ...,
    verify: TLSVerifyType | None = ...,
    cert: TLSClientCertType | None = ...,
    json: typing.Any | None = ...,
    retries: RetryType = ...,
) -> AsyncResponse: ...


async def request(
    method: HttpMethodType,
    url: str,
    *,
    params: QueryParameterType | None = None,
    data: BodyType | AsyncBodyType | None = None,
    headers: HeadersType | None = None,
    cookies: CookiesType | None = None,
    files: MultiPartFilesType | MultiPartFilesAltType | None = None,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
    timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
    proxies: ProxyType | None = None,
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    stream: bool | None = None,
    verify: TLSVerifyType | None = None,
    cert: TLSClientCertType | None = None,
    json: typing.Any | None = None,
    retries: RetryType = DEFAULT_RETRIES,
) -> Response | AsyncResponse:
    """Constructs and sends a :class:`Request <Request>`. This does not keep the connection alive.
    Use an :class:`AsyncSession` to reuse the connection.

    :param method: method for the new :class:`Request` object: ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``,
        or ``DELETE``.
    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``)
        for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.
    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`

    Usage::

      >>> import niquests
      >>> req = await niquests.arequest('GET', 'https://httpbin.org/get')
      >>> req
      <Response HTTP/2 [200]>
    """

    # By using the 'with' statement we are sure the session is closed, thus we
    # avoid leaving sockets open which can trigger a ResourceWarning in some
    # cases, and look like a memory leak in others.
    async with AsyncSession(quic_cache_layer=_SHARED_QUIC_CACHE, retries=retries) as session:
        if _SHARED_OCSP_CACHE is not None:
            session._ocsp_cache = _SHARED_OCSP_CACHE.get()

        return await session.request(  # type: ignore[misc]
            method,
            url,
            params,
            data,
            headers,
            cookies,
            files,
            auth,
            timeout,
            allow_redirects,
            proxies,
            hooks,
            stream,  # type: ignore[arg-type]
            verify,
            cert,
            json,
        )


@typing.overload
async def get(
    url: str,
    params: QueryParameterType | None = ...,
    *,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | None = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> Response: ...


@typing.overload
async def get(
    url: str,
    params: QueryParameterType | None = ...,
    *,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> AsyncResponse: ...


async def get(
    url: str,
    params: QueryParameterType | None = None,
    *,
    headers: HeadersType | None = None,
    cookies: CookiesType | None = None,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
    timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
    proxies: ProxyType | None = None,
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
    **kwargs: typing.Any,
) -> Response | AsyncResponse:
    r"""Sends a GET request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.
    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "GET",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        allow_redirects=allow_redirects,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
        **kwargs,
    )


@typing.overload
async def options(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> Response: ...


@typing.overload
async def options(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> AsyncResponse: ...


async def options(
    url: str,
    *,
    params: QueryParameterType | None = None,
    headers: HeadersType | None = None,
    cookies: CookiesType | None = None,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
    timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
    proxies: ProxyType | None = None,
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
    **kwargs: typing.Any,
) -> Response | AsyncResponse:
    r"""Sends an OPTIONS request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "OPTIONS",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        allow_redirects=allow_redirects,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
        **kwargs,
    )


@typing.overload
async def head(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> Response: ...


@typing.overload
async def head(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> AsyncResponse: ...


async def head(
    url: str,
    *,
    params: QueryParameterType | None = None,
    headers: HeadersType | None = None,
    cookies: CookiesType | None = None,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
    timeout: TimeoutType | None = READ_DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
    proxies: ProxyType | None = None,
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
    **kwargs: typing.Any,
) -> Response | AsyncResponse:
    r"""Sends a HEAD request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "HEAD",
        url,
        allow_redirects=allow_redirects,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
        **kwargs,
    )


@typing.overload
async def post(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> Response: ...


@typing.overload
async def post(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> AsyncResponse: ...


async def post(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
) -> Response | AsyncResponse:
    r"""Sends a POST request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or (awaitable or not) file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``)
        for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
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
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
    )


@typing.overload
async def put(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> Response: ...


@typing.overload
async def put(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> AsyncResponse: ...


async def put(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
) -> Response | AsyncResponse:
    r"""Sends a PUT request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or (awaitable or not) file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``)
        for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "PUT",
        url,
        data=data,
        params=params,
        json=json,
        headers=headers,
        cookies=cookies,
        files=files,
        auth=auth,
        timeout=timeout,
        allow_redirects=allow_redirects,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
    )


@typing.overload
async def patch(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> Response: ...


@typing.overload
async def patch(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
) -> AsyncResponse: ...


async def patch(
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
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
) -> Response | AsyncResponse:
    r"""Sends a PATCH request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or (awaitable or not) file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``)
        for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "PATCH",
        url,
        data=data,
        params=params,
        json=json,
        headers=headers,
        cookies=cookies,
        files=files,
        auth=auth,
        timeout=timeout,
        allow_redirects=allow_redirects,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
    )


@typing.overload
async def delete(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[False] | typing.Literal[None] = ...,
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> Response: ...


@typing.overload
async def delete(
    url: str,
    *,
    params: QueryParameterType | None = ...,
    headers: HeadersType | None = ...,
    cookies: CookiesType | None = ...,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = ...,
    timeout: TimeoutType | None = ...,
    allow_redirects: bool = ...,
    proxies: ProxyType | None = ...,
    hooks: AsyncHookType[PreparedRequest | Response] | None = ...,
    verify: TLSVerifyType | None = ...,
    stream: typing.Literal[True],
    cert: TLSClientCertType | None = ...,
    retries: RetryType = ...,
    **kwargs: typing.Any,
) -> AsyncResponse: ...


async def delete(
    url: str,
    *,
    params: QueryParameterType | None = None,
    headers: HeadersType | None = None,
    cookies: CookiesType | None = None,
    auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
    timeout: TimeoutType | None = WRITE_DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
    proxies: ProxyType | None = None,
    hooks: AsyncHookType[PreparedRequest | Response] | None = None,
    verify: TLSVerifyType | None = None,
    stream: bool | None = None,
    cert: TLSClientCertType | None = None,
    retries: RetryType = DEFAULT_RETRIES,
    **kwargs: typing.Any,
) -> Response | AsyncResponse:
    r"""Sends a DELETE request. This does not keep the connection alive. Use an :class:`AsyncSession` to reuse the connection.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection.
            Defaults to ``True``.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a path passed as a string or os.Pathlike object,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
            It is also possible to put the certificates (directly) in a string or bytes.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded. Otherwise, the response will
            be of type :class:`AsyncResponse <AsyncResponse>` so that it will be awaitable.
    :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair, or ('cert', 'key', 'key_password').
    :param hooks: (optional) Register functions that should be called at very specific moment in the request lifecycle.
    :param retries: (optional) If integer, determine the number of retry in case of a timeout or connection error.
            Otherwise, for fine gained retry, use directly a ``Retry`` instance from urllib3.

    :return: :class:`Response <Response>` object if stream=None or False. Otherwise :class:`AsyncResponse <AsyncResponse>`
    """
    return await request(  # type: ignore[misc]
        "DELETE",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        allow_redirects=allow_redirects,
        proxies=proxies,
        verify=verify,
        stream=stream,  # type: ignore[arg-type]
        cert=cert,
        hooks=hooks,
        retries=retries,
        **kwargs,
    )
