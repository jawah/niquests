from __future__ import annotations

import time
import typing
from datetime import timedelta

from ..._constant import DEFAULT_RETRIES
from ...adapters import BaseAdapter
from ...exceptions import InvalidSchema, SSLError
from ...models import PreparedRequest, Response
from ...packages.urllib3._collections import HTTPHeaderDict
from ...packages.urllib3._constant import DEFAULT_BLOCKSIZE
from ...packages.urllib3._constant import responses as status_reasons
from ...packages.urllib3.backend import LowLevelResponse
from ...packages.urllib3.exceptions import MaxRetryError
from ...packages.urllib3.response import HTTPResponse as BaseHTTPResponse
from ...packages.urllib3.util import Timeout as TimeoutSauce
from ...packages.urllib3.util.request import body_to_chunks
from ...packages.urllib3.util.retry import Retry
from ...structures import CaseInsensitiveDict
from ...utils import get_encoding_from_headers, rewind_body
from . import _capabilities
from ._sse import WASISSEExtension
from ._utils import (
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

if typing.TYPE_CHECKING:
    from ...typing import ProxyType, RetryType, TLSClientCertType, TLSVerifyType

if not _capabilities.HAS_WASI_P2_HTTP:
    raise ImportError(
        "The synchronous WASI HTTP adapter requires wasi:http/types@0.2.x and "
        "wasi:http/outgoing-handler@0.2.x in the component world."
    )

from componentize_py_types import Err as _Err  # type: ignore[import-not-found]  # noqa: E402
from componentize_py_types import Ok as _Ok  # type: ignore[import-not-found]  # noqa: E402
from wit_world.imports.streams import StreamError_Closed as _StreamErrorClosed  # type: ignore[import-not-found]  # noqa: E402

_TYPES = typing.cast(typing.Any, _capabilities._WASI_P2_HTTP_TYPES)
_OUTGOING_HANDLER = typing.cast(typing.Any, _capabilities._WASI_P2_HTTP_HANDLER)


def _rewind_body_for_retry(request: PreparedRequest) -> None:
    if request.body is not None and (request._body_position is not None or hasattr(request.body, "__next__")):
        rewind_body(request)


def _unwrap(value: typing.Any) -> typing.Any:
    if isinstance(value, _Err):
        raise typing.cast(BaseException, value)
    return getattr(value, "value", value) if isinstance(value, _Ok) else value


class _WASILowLevelResponse(LowLevelResponse):
    def __init__(
        self,
        method: str,
        status: int,
        reason: str,
        headers: HTTPHeaderDict,
        body: typing.Any,
        stream: typing.Any,
        url: str,
    ) -> None:
        self._body = body
        self._stream = stream
        self._url = url
        self._trailers_resource = None
        self._trailers_future = None
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

    def _read_body(self, amount: int | None, stream_id: int | None) -> tuple[list[bytes], bool, HTTPHeaderDict | None]:
        chunks: list[bytes] = []
        while True:
            try:
                chunk = self._stream.read(max(amount or 16 * 1024, 1))
                if chunk:
                    chunks.append(bytes(chunk))
                    if amount is not None:
                        return chunks, False, None
                    continue
                pollable = self._stream.subscribe()
                try:
                    pollable.block()
                finally:
                    close_resource(pollable)
            except BaseException as exc:
                if not isinstance(exc, _Err):
                    raise
                if isinstance(exc.value, _StreamErrorClosed):  # type: ignore[attr-defined]
                    return chunks, True, self._finish()
                with wasi_exception_mapping(self._url, reading=True):
                    raise

    def _finish(self) -> HTTPHeaderDict | None:
        close_resource(self._stream)
        self._stream = None
        trailers_dict = None
        if self._body is not None:
            try:
                with wasi_exception_mapping(self._url, reading=True):
                    future = _TYPES.IncomingBody.finish(self._body)
                    self._trailers_future = future
                    self._body = None
                    while True:
                        result = future.get()
                        if result is None:
                            pollable = future.subscribe()
                            try:
                                pollable.block()
                            finally:
                                close_resource(pollable)
                            continue
                        trailers = _unwrap(_unwrap(result))
                        if trailers is not None:
                            self._trailers_resource = trailers
                            trailers_dict = HTTPHeaderDict()
                            for name, value in trailers.entries():
                                trailers_dict.add(name, decode_field_value(value))
                        break
            finally:
                close_resource(self._trailers_resource)
                self._trailers_resource = None
                close_resource(self._trailers_future)
                self._trailers_future = None
        return trailers_dict

    def _abort_wasi(self, stream_id: int) -> None:
        close_resource(self._stream)
        self._stream = None
        close_resource(self._body)
        self._body = None

    def close(self) -> None:
        if self._stream is not None or self._body is not None:
            self._abort_wasi(0)
        close_resource(self._trailers_resource)
        self._trailers_resource = None
        close_resource(self._trailers_future)
        self._trailers_future = None
        super().close()


class _WASIHTTPResponse(BaseHTTPResponse):
    def close(self) -> None:
        if isinstance(self._fp, _WASILowLevelResponse):
            self._fp.abort()
        super().close()

    def release_conn(self) -> None:
        pass


class WASIAdapter(BaseAdapter):
    """Synchronous adapter backed by WASI HTTP 0.2."""

    def __init__(self, max_retries: RetryType = DEFAULT_RETRIES) -> None:
        super().__init__()
        self.max_retries = max_retries if isinstance(max_retries, Retry) else Retry.from_int(max_retries)

    def __repr__(self) -> str:
        return "<WASIAdapter HTTP/0.2>"

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | tuple | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], None] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], None] | None = None,
        on_early_response: typing.Callable[[Response], None] | None = None,
        multiplexed: bool = False,
    ) -> Response:
        started = time.time()
        retries = self.max_retries
        method = request.method or "GET"
        while True:
            try:
                response = self._send_once(
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
                _rewind_body_for_retry(request)
                retries.sleep()
                continue

            retry_response = BaseHTTPResponse(
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
                        response.close()
                        raise
                    response.elapsed = timedelta(seconds=time.time() - started)
                    return response
                response.close()
                _rewind_body_for_retry(request)
                retries.sleep(retry_response)
                continue

            response.elapsed = timedelta(seconds=time.time() - started)
            return response

    def _send_once(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: int | float | tuple | TimeoutSauce | None = None,
        verify: TLSVerifyType = True,
        cert: TLSClientCertType | None = None,
        proxies: ProxyType | None = None,
        on_post_connection: typing.Callable[[typing.Any], None] | None = None,
        on_upload_body: typing.Callable[[int, int | None, bool, bool], None] | None = None,
        on_early_response: typing.Callable[[Response], None] | None = None,
        multiplexed: bool = False,
    ) -> Response:
        started = time.time()
        scheme, authority, path = validate_transport_options(request, verify, cert, proxies)
        original_scheme = (request.url or "").split(":", 1)[0].lower()
        is_sse = original_scheme in ("sse", "psse")

        with wasi_exception_mapping(request.url or ""):
            fields = _TYPES.Fields.from_list(request_headers(request, sse=is_sse))
            outgoing = _TYPES.OutgoingRequest(fields)
            outgoing.set_method(method_variant(_TYPES, request.method or "GET"))
            outgoing.set_scheme(scheme_variant(_TYPES, scheme))
            outgoing.set_authority(authority)
            outgoing.set_path_with_query(path)

            options = _TYPES.RequestOptions()
            set_timeouts(options, timeout)
            body = request.body
            prepared_body = body_to_chunks(body, request.method or "GET", DEFAULT_BLOCKSIZE, force=True)
            outgoing_body = outgoing.body() if body is not None else None
            future = _OUTGOING_HANDLER.handle(outgoing, options)
            incoming = None

            if outgoing_body is not None:
                output = outgoing_body.write()
                sent = 0
                content_length = request.headers.get("Content-Length") if request.headers is not None else None
                try:
                    total = int(content_length) if content_length is not None else prepared_body.content_length
                except (TypeError, ValueError):  # Defensive: PreparedRequest emits a valid length
                    total = prepared_body.content_length
                try:
                    stop_upload = False
                    chunks = prepared_body.chunks
                    assert chunks is not None and not hasattr(chunks, "__aiter__")
                    for chunk in chunks:
                        chunk = chunk.encode("utf-8") if isinstance(chunk, str) else bytes(chunk)
                        offset = 0
                        while offset < len(chunk):
                            permit = output.check_write()
                            if permit == 0:  # Defensive: depends on host output-buffer saturation
                                pollable = output.subscribe()
                                try:
                                    pollable.block()
                                finally:
                                    close_resource(pollable)
                                continue
                            count = min(permit, len(chunk) - offset)
                            output.write(chunk[offset : offset + count])
                            offset += count
                            sent += count
                            if on_upload_body is not None:  # Defensive: Session always supplies the callback
                                on_upload_body(sent, total, False, False)
                            result = future.get()
                            if result is not None:  # Defensive: racing condition?
                                incoming = _unwrap(_unwrap(result))
                                close_resource(future)
                                stop_upload = True
                                break
                        if stop_upload:  # Defensive: early final-response branch
                            chunks.close()
                            break
                    if not stop_upload:  # Defensive: host timing-dependent
                        output.flush()
                        pollable = output.subscribe()
                        try:
                            pollable.block()
                        finally:
                            close_resource(pollable)
                        output.check_write()
                except BaseException:  # Defensive: upload failure cleanup
                    if on_upload_body is not None:
                        on_upload_body(sent, total, True, True)
                    raise
                finally:
                    close_resource(output)
                _TYPES.OutgoingBody.finish(outgoing_body, None)
                if on_upload_body is not None:  # Defensive: Session always supplies the callback
                    on_upload_body(sent, total, True, False)

            if incoming is None:  # Defensive: response timing/race before end request
                while True:
                    result = future.get()
                    if result is None:
                        pollable = future.subscribe()
                        try:
                            pollable.block()
                        finally:
                            close_resource(pollable)
                        continue
                    incoming = _unwrap(_unwrap(result))
                    close_resource(future)
                    break
        header_resource = incoming.headers()
        try:
            header_entries = header_resource.entries()
            low_headers = response_headers(header_entries)
        finally:
            close_resource(header_resource)
        status_code = incoming.status()
        with wasi_exception_mapping(request.url or "", reading=True):
            incoming_body = incoming.consume()
            input_stream = incoming_body.stream()
        close_resource(incoming)

        reason = status_reasons.get(status_code, "")
        low_response = _WASILowLevelResponse(
            request.method or "GET",
            status_code,
            reason,
            low_headers,
            incoming_body,
            input_stream,
            request.url or "",
        )
        raw = _WASIHTTPResponse(
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
            raw._extension = WASISSEExtension(raw)
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        elif stream:
            response._content = False  # type: ignore[assignment]
            response._content_consumed = False
        else:
            response._content = raw.read()
            response._content_consumed = True

        response.elapsed = timedelta(seconds=time.time() - started)
        return response

    def close(self) -> None:
        pass


__all__ = ("WASIAdapter",)
