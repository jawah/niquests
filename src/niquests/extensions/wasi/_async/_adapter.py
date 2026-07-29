from __future__ import annotations

import time
import typing
from datetime import timedelta
from inspect import iscoroutinefunction

from ...._constant import DEFAULT_RETRIES
from ....adapters import AsyncBaseAdapter
from ....exceptions import InvalidSchema, SSLError
from ....models import AsyncResponse, PreparedRequest, Response
from ....packages.urllib3._async.response import AsyncHTTPResponse as BaseAsyncHTTPResponse
from ....packages.urllib3._collections import HTTPHeaderDict
from ....packages.urllib3._constant import DEFAULT_BLOCKSIZE
from ....packages.urllib3._constant import responses as status_reasons
from ....packages.urllib3.backend._async import AsyncLowLevelResponse
from ....packages.urllib3.exceptions import MaxRetryError
from ....packages.urllib3.util import Timeout as TimeoutSauce
from ....packages.urllib3.util.request import body_to_chunks
from ....packages.urllib3.util.retry import Retry
from ....structures import CaseInsensitiveDict
from ....utils import _swap_context, arewind_body, get_encoding_from_headers, rewind_body
from .. import _capabilities
from .._utils import (
    _WASIProxyError,
    close_resource,
    decode_field_value,
    method_variant,
    request_headers,
    response_headers,
    scheme_variant,
    set_timeouts,
    validate_transport_options,
    wasi_exception_mapping,
)
from ._sse import AsyncWASISSEExtension

if typing.TYPE_CHECKING:
    from ....typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType

if not _capabilities.HAS_WASI_P3_HTTP:
    raise ImportError(
        "The asynchronous WASI HTTP adapter requires wasi:http/types@0.3.0 and wasi:http/client@0.3.0 in the component world."
    )

import componentize_py_async_support as _async_support  # type: ignore[import-not-found]  # noqa: E402
import wit_world as _wit_world  # type: ignore[import-not-found]  # noqa: E402
from componentize_py_types import Err as _Err  # type: ignore[import-not-found]  # noqa: E402
from componentize_py_types import Ok as _Ok  # type: ignore[import-not-found]  # noqa: E402

_TYPES = typing.cast(typing.Any, _capabilities._WASI_P3_HTTP_TYPES)
_CLIENT = typing.cast(typing.Any, _capabilities._WASI_P3_HTTP_CLIENT)


async def _rewind_body_for_retry(request: PreparedRequest) -> None:
    if request.body is None or not (
        request._body_position is not None or hasattr(request.body, "__next__") or hasattr(request.body, "__anext__")
    ):
        return
    if hasattr(request.body, "seek") and iscoroutinefunction(request.body.seek):
        await arewind_body(request)
    else:
        rewind_body(request)


def _trailers_future() -> typing.Any:
    factory = _wit_world.result_option_wasi_http_types_fields_wasi_http_types_error_code_future
    return factory(lambda: _Ok(None))[1]


def _unit_future() -> typing.Any:
    factory = _wit_world.result_unit_wasi_http_types_error_code_future
    return factory(lambda: _Ok(None))[1]


async def _write_body(
    writer: typing.Any,
    chunks: typing.Iterable[bytes] | typing.AsyncIterable[bytes],
    total: int | None,
    on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None,
) -> None:
    sent = 0
    failed = False
    try:
        with writer:
            if hasattr(chunks, "__aiter__"):  # Defensive: both iterable kinds are covered separately
                async for chunk in typing.cast(typing.AsyncIterable[bytes], chunks):
                    written = await writer.write_all(chunk)
                    sent += written
                    if on_upload_body is not None:
                        await on_upload_body(sent, total, False, False)
            else:
                for chunk in typing.cast(typing.Iterable[bytes], chunks):
                    chunk = chunk.encode("utf-8") if isinstance(chunk, str) else bytes(chunk)
                    written = await writer.write_all(chunk)
                    sent += written
                    if on_upload_body is not None:  # Defensive: Session always supplies the callback
                        await on_upload_body(sent, total, False, False)
    except BaseException:  # Defensive: upload failure cleanup
        failed = True
        if on_upload_body is not None:
            await on_upload_body(sent, total, True, True)
    if not failed and on_upload_body is not None:  # Defensive:
        await on_upload_body(sent, total, True, False)


def _unwrap_result(value: typing.Any) -> typing.Any:
    if isinstance(value, _Err):
        raise value
    return getattr(value, "value", value)


class _AsyncWASILowLevelResponse(AsyncLowLevelResponse):
    def __init__(
        self,
        method: str,
        status: int,
        reason: str,
        headers: HTTPHeaderDict,
        reader: typing.Any,
        trailers_future: typing.Any,
        request_done: typing.Any,
        url: str,
    ) -> None:
        self._reader = reader
        self._trailers_future = trailers_future
        self._request_done = request_done
        self._url = url
        super().__init__(
            method,
            status,
            0,
            reason,
            headers,
            self._read_body,
            stream_id=0,
            stream_abort=self._abort_wasi,
        )

    async def _finish(self) -> HTTPHeaderDict | None:
        close_resource(self._reader)
        self._reader = None
        trailers_dict = None
        try:
            with wasi_exception_mapping(self._url, reading=True):
                if self._trailers_future is not None:
                    result = await self._trailers_future.read()
                    value = _unwrap_result(result)
                    if value is not None:
                        try:
                            trailers_dict = HTTPHeaderDict()
                            for name, trailer_value in value.copy_all():
                                trailers_dict.add(name, decode_field_value(trailer_value))
                        finally:
                            close_resource(value)
                if self._request_done is not None:
                    result = await self._request_done.read()
                    _unwrap_result(result)
        finally:
            close_resource(self._trailers_future)
            close_resource(self._request_done)
            self._trailers_future = self._request_done = None
        return trailers_dict

    async def _read_body(self, amount: int | None, stream_id: int | None) -> tuple[list[bytes], bool, HTTPHeaderDict | None]:
        chunks: list[bytes] = []
        while True:
            with wasi_exception_mapping(self._url, reading=True):
                chunk = bytes(await self._reader.read(max(amount or 16 * 1024, 1)))
            if chunk:
                chunks.append(chunk)
                if amount is not None:
                    return chunks, False, None
                continue
            if self._reader.writer_dropped:
                return chunks, True, await self._finish()

    async def _abort_wasi(self, stream_id: int) -> None:
        close_resource(self._reader)
        close_resource(self._trailers_future)
        close_resource(self._request_done)
        self._reader = self._trailers_future = self._request_done = None


class _AsyncWASIHTTPResponse(BaseAsyncHTTPResponse):
    async def close(self) -> None:
        if isinstance(self._fp, _AsyncWASILowLevelResponse):
            await self._fp.abort()
        await super().close()

    def release_conn(self) -> None:
        pass


class AsyncWASIAdapter(AsyncBaseAdapter):
    """Asynchronous adapter backed by WASI HTTP 0.3."""

    def __init__(self, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        super().__init__()
        self.max_retries = max_retries if isinstance(max_retries, Retry) else Retry.from_int(max_retries)

    def __repr__(self) -> str:
        return "<AsyncWASIAdapter HTTP/0.3>"

    async def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | tuple | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], typing.Awaitable[None]] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None = None,
        on_early_response: typing.Callable[[Response], typing.Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> AsyncResponse:
        started = time.time()
        retries = self.max_retries
        method = request.method or "GET"
        while True:
            try:
                response = await self._send_once(
                    request,
                    stream,
                    timeout,
                    verify,
                    cert,
                    proxies,
                    on_post_connection,
                    on_upload_body,
                    on_early_response,
                    multiplexed,
                )
            except (InvalidSchema, RuntimeError, SSLError, _WASIProxyError):
                raise
            except Exception as exc:
                retries = retries.increment(method, request.url, error=exc)
                await _rewind_body_for_retry(request)
                await retries.async_sleep()
                continue

            retry_response = BaseAsyncHTTPResponse(
                body=b"",
                headers=response.headers,
                status=response.status_code,
                request_method=request.method,
                request_url=request.url,
            )
            has_retry_after = bool(response.headers.get("Retry-After"))
            if retries.is_retry(method, response.status_code, has_retry_after):
                try:
                    retries = retries.increment(method, request.url, response=retry_response)
                except MaxRetryError:
                    if retries.raise_on_status:
                        await response.close()
                        raise
                    response.elapsed = timedelta(seconds=time.time() - started)
                    return response
                await response.close()
                await _rewind_body_for_retry(request)
                await retries.async_sleep(retry_response)
                continue

            response.elapsed = timedelta(seconds=time.time() - started)
            return response

    async def _send_once(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | tuple | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], typing.Awaitable[None]] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], typing.Awaitable[None]] | None = None,
        on_early_response: typing.Callable[[Response], typing.Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> AsyncResponse:
        started = time.time()
        scheme, authority, path = validate_transport_options(request, verify, cert, proxies)
        original_scheme = (request.url or "").split(":", 1)[0].lower()
        is_sse = original_scheme in ("sse", "psse")

        body = request.body
        body_reader = None
        if body is not None:
            prepared_body = body_to_chunks(body, request.method or "GET", DEFAULT_BLOCKSIZE, force=True)
            assert prepared_body.chunks is not None
            content_length_header = request.headers.get("Content-Length") if request.headers is not None else None
            try:
                content_length = (
                    int(content_length_header) if content_length_header is not None else prepared_body.content_length
                )
            except (TypeError, ValueError):  # Defensive: PreparedRequest emits a valid length
                content_length = prepared_body.content_length
            writer, body_reader = _wit_world.byte_stream()
            _async_support.spawn(_write_body(writer, prepared_body.chunks, content_length, on_upload_body))

        options = _TYPES.RequestOptions()
        set_timeouts(options, timeout)
        with wasi_exception_mapping(request.url or ""):
            fields = _TYPES.Fields.from_list(request_headers(request, sse=is_sse))
            outgoing, request_done = _TYPES.Request.new(fields, body_reader, _trailers_future(), options)
            outgoing.set_method(method_variant(_TYPES, request.method or "GET"))
            outgoing.set_scheme(scheme_variant(_TYPES, scheme))
            outgoing.set_authority(authority)
            outgoing.set_path_with_query(path)
            incoming = await _CLIENT.send(outgoing)

        status_code = incoming.get_status_code()
        header_resource = incoming.get_headers()
        try:
            header_entries = header_resource.copy_all()
            low_headers = response_headers(header_entries)
        finally:
            close_resource(header_resource)
        reader, trailers = _TYPES.Response.consume_body(incoming, _unit_future())
        reason = status_reasons.get(status_code, "")
        low_response = _AsyncWASILowLevelResponse(
            request.method or "GET",
            status_code,
            reason,
            low_headers,
            reader,
            trailers,
            request_done,
            request.url or "",
        )
        raw = _AsyncWASIHTTPResponse(
            body=low_response,
            headers=low_headers,
            status=status_code,
            version=0,
            reason=reason,
            preload_content=False,
            decode_content=True,
            original_response=low_response,
            enforce_content_length=True,
            request_method=request.method,
            request_url=request.url,
        )

        response = Response()
        response.status_code = status_code
        response.headers = CaseInsensitiveDict(low_headers)
        response.request = request
        response.url = request.url
        response.reason = reason
        response.encoding = get_encoding_from_headers(low_headers)
        response.raw = raw  # type: ignore[assignment]

        if is_sse:
            raw._extension = AsyncWASISSEExtension(raw)
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        elif stream:
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        else:
            response._content = await raw.read()
            response._content_consumed = True

        response.elapsed = timedelta(seconds=time.time() - started)
        _swap_context(response)
        return response  # type: ignore[return-value]

    async def close(self) -> None:
        pass


__all__ = ("AsyncWASIAdapter",)
