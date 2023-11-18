from __future__ import annotations

import typing

from ._constant import READ_DEFAULT_TIMEOUT, WRITE_DEFAULT_TIMEOUT
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
)
from .extensions._sync_to_async import sync_to_async
from .hooks import dispatch_hook
from .models import PreparedRequest, Request, Response
from .sessions import Session


class AsyncSession(Session):
    """
    "It's aint much, but its honest work" kind of class.
    Use a thread pool under the carpet. It's not true async.
    """

    disable_thread: bool = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, value, tb):
        super().__exit__()

    async def send(self, request: PreparedRequest, **kwargs: typing.Any) -> Response:  # type: ignore[override]
        return await sync_to_async(
            super().send,
            thread_sensitive=AsyncSession.disable_thread,
        )(request=request, **kwargs)

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
        stream: bool | None = None,
        verify: TLSVerifyType | None = None,
        cert: TLSClientCertType | None = None,
        json: typing.Any | None = None,
    ) -> Response:
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
            "pre_request", hooks, self.prepare_request(req)  # type: ignore[arg-type]
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
    ) -> Response:
        return await self.request(
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
