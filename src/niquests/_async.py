from __future__ import annotations

import asyncio
import typing
import json as _json
from charset_normalizer import from_bytes
import codecs

if typing.TYPE_CHECKING:
    from typing_extensions import Literal

from ._compat import HAS_LEGACY_URLLIB3

if HAS_LEGACY_URLLIB3 is False:
    from urllib3.exceptions import (
        DecodeError,
        ProtocolError,
        ReadTimeoutError,
        SSLError,
    )
else:
    from urllib3_future.exceptions import (  # type: ignore[assignment]
        DecodeError,
        ProtocolError,
        ReadTimeoutError,
        SSLError,
    )

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
    ResolverType,
    CacheLayerAltSvcType,
    RetryType,
)
from .extensions._sync_to_async import sync_to_async
from .exceptions import (
    ChunkedEncodingError,
    ConnectionError,
    ContentDecodingError,
    StreamConsumedError,
)
from .exceptions import JSONDecodeError as RequestsJSONDecodeError
from .exceptions import SSLError as RequestsSSLError
from .hooks import dispatch_hook
from .models import PreparedRequest, Request, Response, ITER_CHUNK_SIZE
from .sessions import Session
from .utils import astream_decode_response_unicode


class AsyncSession(Session):
    """
    "It's aint much, but its honest work" kind of class.
    Use a thread pool under the carpet. It's not true async.
    """

    disable_thread: bool = False
    semaphore: asyncio.Semaphore = asyncio.Semaphore(10)

    def __init__(
        self,
        *,
        resolver: ResolverType | None = None,
        source_address: tuple[str, int] | None = None,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        retries: RetryType = DEFAULT_RETRIES,
        multiplexed: bool = False,
        disable_http2: bool = False,
        disable_http3: bool = False,
        disable_ipv6: bool = False,
        disable_ipv4: bool = False,
        pool_connections: int = DEFAULT_POOLSIZE,
        pool_maxsize: int = DEFAULT_POOLSIZE,
    ):
        super().__init__(
            resolver=resolver,
            source_address=source_address,
            quic_cache_layer=quic_cache_layer,
            retries=retries,
            multiplexed=multiplexed,
            disable_http2=disable_http2,
            disable_http3=disable_http3,
            disable_ipv6=disable_ipv6,
            disable_ipv4=disable_ipv4,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )
        self._semaphore = asyncio.Semaphore(pool_maxsize)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, value, tb):
        await self.close()

    async def send(  # type: ignore[override]
        self, request: PreparedRequest, **kwargs: typing.Any
    ) -> Response | AsyncResponse:  # type: ignore[override]
        if "stream" in kwargs and kwargs["stream"]:
            kwargs["mutate_response_class"] = AsyncResponse
        await AsyncSession.semaphore.acquire()
        try:
            return await sync_to_async(
                super().send,
                thread_sensitive=AsyncSession.disable_thread,
            )(request=request, **kwargs)
        finally:
            AsyncSession.semaphore.release()

    @typing.overload  # type: ignore[override]
    async def request(
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = ...,
        data: BodyType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        stream: Literal[False] = ...,
        verify: TLSVerifyType | None = ...,
        cert: TLSClientCertType | None = ...,
        json: typing.Any | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def request(
        self,
        method: HttpMethodType,
        url: str,
        params: QueryParameterType | None = ...,
        data: BodyType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        *,
        stream: Literal[True],
        verify: TLSVerifyType | None = ...,
        cert: TLSClientCertType | None = ...,
        json: typing.Any | None = ...,
    ) -> AsyncResponse:
        ...

    async def request(  # type: ignore[override]
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

        return await self.send(prep, **send_kwargs)

    @typing.overload  # type: ignore[override]
    async def get(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def get(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def get(  # type: ignore[override]
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
        )

    @typing.overload  # type: ignore[override]
    async def options(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def options(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def options(  # type: ignore[override]
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
        )

    @typing.overload  # type: ignore[override]
    async def head(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def head(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def head(  # type: ignore[override]
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
        )

    @typing.overload  # type: ignore[override]
    async def post(
        self,
        url: str,
        data: BodyType | None = ...,
        json: typing.Any | None = ...,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def post(
        self,
        url: str,
        data: BodyType | None = ...,
        json: typing.Any | None = ...,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def post(  # type: ignore[override]
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
        data: BodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def put(
        self,
        url: str,
        data: BodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def put(  # type: ignore[override]
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
        data: BodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def patch(
        self,
        url: str,
        data: BodyType | None = ...,
        *,
        json: typing.Any | None = ...,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        files: MultiPartFilesType | MultiPartFilesAltType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def patch(  # type: ignore[override]
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
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[False] = ...,
        cert: TLSClientCertType | None = ...,
    ) -> Response:
        ...

    @typing.overload  # type: ignore[override]
    async def delete(
        self,
        url: str,
        *,
        params: QueryParameterType | None = ...,
        headers: HeadersType | None = ...,
        cookies: CookiesType | None = ...,
        auth: HttpAuthenticationType | None = ...,
        timeout: TimeoutType | None = ...,
        allow_redirects: bool = ...,
        proxies: ProxyType | None = ...,
        hooks: HookType[PreparedRequest | Response] | None = ...,
        verify: TLSVerifyType = ...,
        stream: Literal[True],
        cert: TLSClientCertType | None = ...,
    ) -> AsyncResponse:
        ...

    async def delete(  # type: ignore[override]
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
        )

    async def gather(self, *responses: Response, max_fetch: int | None = None) -> None:  # type: ignore[override]
        return await sync_to_async(
            super().gather,
            thread_sensitive=AsyncSession.disable_thread,
        )(*responses, max_fetch=max_fetch)

    async def close(self) -> None:  # type: ignore[override]
        await sync_to_async(
            super().close,
            thread_sensitive=AsyncSession.disable_thread,
        )()


class AsyncResponse(Response):
    def __aenter__(self) -> AsyncResponse:
        return self

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in await self.iter_content(ITER_CHUNK_SIZE):
            yield chunk

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @typing.overload  # type: ignore[override]
    async def iter_content(
        self, chunk_size: int = ..., decode_unicode: Literal[False] = ...
    ) -> typing.AsyncGenerator[bytes, None]:
        ...

    @typing.overload  # type: ignore[override]
    async def iter_content(
        self, chunk_size: int = ..., *, decode_unicode: Literal[True]
    ) -> typing.AsyncGenerator[str, None]:
        ...

    async def iter_content(  # type: ignore[override]
        self, chunk_size: int = ITER_CHUNK_SIZE, decode_unicode: bool = False
    ) -> typing.AsyncGenerator[bytes | str, None]:
        async def generate() -> (
            typing.AsyncGenerator[
                bytes,
                None,
            ]
        ):
            assert self.raw is not None

            while True:
                try:
                    chunk = await sync_to_async(
                        self.raw.read, thread_sensitive=AsyncSession.disable_thread
                    )(
                        chunk_size,
                        decode_content=True,
                    )
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)

                if not chunk:
                    break

                yield chunk

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(
                f"chunk_size must be an int, it is instead a {type(chunk_size)}."
            )

        stream_chunks = generate()

        if decode_unicode:
            return astream_decode_response_unicode(stream_chunks, self)

        return stream_chunks

    @typing.overload  # type: ignore[override]
    async def iter_lines(
        self,
        chunk_size: int = ...,
        decode_unicode: Literal[False] = ...,
        delimiter: str | bytes | None = ...,
    ) -> typing.AsyncGenerator[bytes, None]:
        ...

    @typing.overload  # type: ignore[override]
    async def iter_lines(
        self,
        chunk_size: int = ...,
        *,
        decode_unicode: Literal[True],
        delimiter: str | bytes | None = ...,
    ) -> typing.AsyncGenerator[str, None]:
        ...

    async def iter_lines(  # type: ignore[misc]
        self,
        chunk_size: int = ITER_CHUNK_SIZE,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> typing.AsyncGenerator[bytes | str, None]:
        if (
            delimiter is not None
            and decode_unicode is False
            and isinstance(delimiter, str)
        ):
            raise ValueError(
                "delimiter MUST match the desired output type. e.g. if decode_unicode is set to True, delimiter MUST be a str, otherwise we expect a bytes-like variable."
            )

        pending = None

        async for chunk in self.iter_content(  # type: ignore[call-overload]
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)  # type: ignore[arg-type]
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            async for line in lines:
                yield line

        if pending is not None:
            yield pending

    @property
    async def content(self) -> bytes | None:  # type: ignore[override]
        return await sync_to_async(
            getattr, thread_sensitive=AsyncSession.disable_thread
        )(super(), "content")

    @property
    async def text(self) -> str | None:  # type: ignore[override]
        content = await self.content

        if not content:
            return ""

        if self.encoding is not None:
            try:
                info = codecs.lookup(self.encoding)

                if (
                    hasattr(info, "_is_text_encoding")
                    and info._is_text_encoding is False
                ):
                    return None
            except LookupError:
                #: We cannot accept unsupported or nonexistent encoding. Override.
                self.encoding = None

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding_guess = from_bytes(content).best()

            if encoding_guess:
                #: We shall cache this inference.
                self.encoding = encoding_guess.encoding
                return str(encoding_guess)

        if self.encoding is None:
            return None

        return str(content, self.encoding, errors="replace")

    async def json(self, **kwargs: typing.Any) -> typing.Any:  # type: ignore[override]
        content = await self.content

        if not content or "json" not in self.headers.get("content-type", "").lower():
            raise RequestsJSONDecodeError(
                "response content is not JSON", await self.text or "", 0
            )

        if not self.encoding:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding_guess = from_bytes(
                content,
                cp_isolation=[
                    "ascii",
                    "utf-8",
                    "utf-16",
                    "utf-32",
                    "utf-16-le",
                    "utf-16-be",
                    "utf-32-le",
                    "utf-32-be",
                ],
            ).best()

            if encoding_guess is not None:
                try:
                    return _json.loads(str(encoding_guess), **kwargs)
                except _json.JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

        plain_content = await self.text

        if plain_content is None:
            raise RequestsJSONDecodeError(
                "response cannot lead to decodable JSON", "", 0
            )

        try:
            return _json.loads(plain_content, **kwargs)
        except _json.JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    async def close(self) -> None:  # type: ignore[override]
        await sync_to_async(
            super().close, thread_sensitive=AsyncSession.disable_thread
        )()
