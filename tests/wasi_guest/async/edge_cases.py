from __future__ import annotations

from io import BytesIO

from componentize_py_types import Err, Ok
from niquests.packages.urllib3._collections import HTTPHeaderDict
from niquests.packages.urllib3.util.retry import Retry

import niquests.extensions.wasi._async._adapter as wasi
from niquests.exceptions import ConnectionError, ReadTimeout
from niquests.models import AsyncResponse, PreparedRequest


class Resource:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True


class Failed:
    pass


class AsyncFuture(Resource):
    def __init__(self, value):
        super().__init__()
        self.value = value

    async def read(self):
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


class Trailer(Resource):
    def copy_all(self):
        return [("x-trailer", b"done")]


class Reader(Resource):
    def __init__(self, values):
        super().__init__()
        self.values = list(values)
        self.writer_dropped = False

    async def read(self, amount):
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        if not self.values and value == b"":
            self.writer_dropped = True
        return value


class Writer(Resource):
    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.data = b""

    async def write_all(self, value):
        if self.fail:
            raise ValueError("write failed")
        self.data += value
        return len(value)


class AsyncRaw:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class AsyncSeekBody:
    def __init__(self, value):
        self.value = value
        self.position = 0

    def read(self):
        value = self.value[self.position :]
        self.position = len(self.value)
        return value

    async def seek(self, position):
        self.position = position


class SSEAsyncRaw:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    async def read(self, amount):
        return self.chunks.pop(0) if self.chunks else b""

    async def close(self):
        self.closed = True


class Fields(Resource):
    @classmethod
    def from_list(cls, values):
        return cls()

    def copy_all(self):
        return []


class Options:
    def set_connect_timeout(self, value):
        pass

    def set_first_byte_timeout(self, value):
        pass

    def set_between_bytes_timeout(self, value):
        pass


class Request:
    @classmethod
    def new(cls, fields, body, trailers, options):
        return cls(), AsyncFuture(Ok(None))

    def set_method(self, value):
        pass

    def set_scheme(self, value):
        pass

    def set_authority(self, value):
        pass

    def set_path_with_query(self, value):
        pass


class Incoming:
    def get_status_code(self):
        return 200

    def get_headers(self):
        return Fields()


class ResponseType:
    @staticmethod
    def consume_body(incoming, result):
        return Reader([b""]), AsyncFuture(Ok(None))


class Types:
    Fields = Fields
    RequestOptions = Options
    Request = Request
    Response = ResponseType

    @staticmethod
    def Method_Get():
        return object()

    Method_Post = Method_Get

    @staticmethod
    def Method_Other(value):
        return value

    @staticmethod
    def Scheme_Http():
        return object()

    Scheme_Https = Scheme_Http


class WitWorld:
    @staticmethod
    def byte_stream():
        return Writer(), Reader([b""])

    @staticmethod
    def result_option_wasi_http_types_fields_wasi_http_types_error_code_future(default):
        return object(), AsyncFuture(Ok(None))

    @staticmethod
    def result_unit_wasi_http_types_error_code_future(default):
        return object(), AsyncFuture(Ok(None))


class AsyncSupport:
    @staticmethod
    def spawn(coroutine):
        coroutine.close()


class Client:
    fail = False

    @classmethod
    async def send(cls, request):
        if cls.fail:
            raise Err(Failed())
        return Incoming()


def prepared(url="https://example.test", method="GET"):
    request = PreparedRequest()
    request.prepare(method=method, url=url)
    return request


async def body_chunk_cases():
    async def chunks():
        yield b"a"
        yield b"b"

    pulses = []

    async def pulse(*values):
        pulses.append(values)

    writer = Writer()
    await wasi._write_body(writer, chunks(), 2, pulse)
    assert writer.data == b"ab" and pulses[-1][2] is True

    async def empty():
        if False:
            yield b""

    await wasi._write_body(Writer(), empty(), None, None)

    failed_pulses = []

    async def failed_pulse(*values):
        failed_pulses.append(values)

    await wasi._write_body(Writer(fail=True), (b"body",), 4, failed_pulse)
    assert failed_pulses[-1][3] is True
    await wasi._write_body(Writer(fail=True), (b"body",), 4, None)
    await wasi._write_body(Writer(), (b"body",), 4, None)
    await wasi._write_body(Writer(), (b"body",), 4, pulse)


async def low_level_cases():
    original = (wasi._Ok, wasi._Err)
    wasi._Ok = Ok
    wasi._Err = Err
    assert wasi._unwrap_result(Ok("ok")) == "ok"
    try:
        wasi._unwrap_result(Err(Failed()))
    except Err:
        pass

    trailers_future = AsyncFuture(Ok(Trailer()))
    request_done = AsyncFuture(Ok(None))
    low = wasi._AsyncWASILowLevelResponse(
        "GET",
        200,
        "OK",
        HTTPHeaderDict(),
        Reader([b"x", b""]),
        trailers_future,
        request_done,
        "url",
    )
    assert await low.read(1) == b"x"
    assert await low.read(1) == b""
    assert low.trailers["x-trailer"] == "done"
    assert trailers_future.closed
    assert request_done.closed

    waits = wasi._AsyncWASILowLevelResponse(
        "GET",
        200,
        "OK",
        HTTPHeaderDict(),
        Reader([b"", b"x", b""]),
        AsyncFuture(Ok(None)),
        None,
        "url",
    )
    assert await waits.read(1) == b"x"
    assert await waits.read(1) == b""

    no_futures = wasi._AsyncWASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Reader([b""]), None, None, "url")
    assert await no_futures.read(1) == b""

    failed = wasi._AsyncWASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Reader([Err(Failed())]), None, None, "url")
    try:
        await failed.read(1)
    except ReadTimeout:
        pass

    other_error = wasi._AsyncWASILowLevelResponse(
        "GET", 200, "OK", HTTPHeaderDict(), Reader([ValueError("bad")]), None, None, "url"
    )
    try:
        await other_error.read(1)
    except ValueError:
        pass

    future_error = wasi._AsyncWASILowLevelResponse(
        "GET", 200, "OK", HTTPHeaderDict(), Reader([b""]), AsyncFuture(Err(Failed())), None, "url"
    )
    try:
        await future_error.read(1)
    except ReadTimeout:
        pass

    unexpected = wasi._AsyncWASILowLevelResponse(
        "GET", 200, "OK", HTTPHeaderDict(), Reader([b""]), AsyncFuture(ValueError("bad")), None, "url"
    )
    try:
        await unexpected.read(1)
    except ValueError:
        pass

    cancellable = wasi._AsyncWASILowLevelResponse(
        "GET",
        200,
        "OK",
        HTTPHeaderDict(),
        Reader([b"pending"]),
        AsyncFuture(Ok(None)),
        AsyncFuture(Ok(None)),
        "url",
    )
    response = wasi._AsyncWASIHTTPResponse(body=cancellable, headers={}, preload_content=False)
    await response.close()
    await response.close()
    response.release_conn()
    assert cancellable._reader is None
    await wasi._AsyncWASIHTTPResponse(body=None, preload_content=False).close()
    wasi._Ok, wasi._Err = original


async def retry_and_adapter_cases():

    adapter = wasi.AsyncWASIAdapter()
    assert repr(adapter) == "<AsyncWASIAdapter HTTP/0.3>"
    await adapter.close()

    attempts = 0
    retrying = wasi.AsyncWASIAdapter(max_retries=Retry(total=1, connect=1))

    async def send_once(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("retry")
        response = AsyncResponse()
        response.status_code = 200
        response.headers = {}
        response.raw = AsyncRaw()
        return response

    retrying._send_once = send_once
    assert (await retrying.send(prepared())).status_code == 200

    attempts = 0
    payloads = []
    body_request = PreparedRequest()
    body_request.prepare(method="PUT", url="https://example.test", data=BytesIO(b"payload"))

    async def send_body_once(request, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        payloads.append(request.body.read())
        if attempts == 1:
            raise ConnectionError("retry")
        response = AsyncResponse()
        response.status_code = 200
        response.headers = {}
        response.raw = AsyncRaw()
        return response

    retrying._send_once = send_body_once
    assert (await retrying.send(body_request)).status_code == 200
    assert payloads == [b"payload", b"payload"]

    async_body = AsyncSeekBody(b"payload")
    body_request.body = async_body
    body_request._body_position = 0
    async_body.position = len(async_body.value)
    await wasi._rewind_body_for_retry(body_request)
    assert async_body.read() == b"payload"

    exhausted = wasi.AsyncWASIAdapter(max_retries=Retry(total=0, status=0, status_forcelist={500}, raise_on_status=False))

    async def status_once(*args, **kwargs):
        response = AsyncResponse()
        response.status_code = 500
        response.headers = {}
        response.raw = AsyncRaw()
        response._content_consumed = False
        return response

    exhausted._send_once = status_once
    assert (await exhausted.send(prepared())).status_code == 500


async def sse_cases():
    raw = SSEAsyncRaw([b": comment\r\n\r\nid: 1\r\nretry: nope\r\ndata: one\r\n\r\ndata: two\r\n\r\n"])
    extension = wasi.AsyncWASISSEExtension(raw)
    assert "id: 1" in await extension.next_payload(raw=True)
    assert (await extension.next_payload()).id == "1"
    assert await extension.next_payload() is None
    await extension.close()
    try:
        await extension.next_payload()
    except OSError:
        pass
    other = wasi.AsyncWASISSEExtension(SSEAsyncRaw([b"id: bad\0id\nretry: 10\nevent: ping\ndata:no-space\n\n"]))
    assert (await other.next_payload()).retry == 10
    await other.close()
    mixed = wasi.AsyncWASISSEExtension(SSEAsyncRaw([b"data: one\r\n\r\ndata: two\n\n"]))
    assert (await mixed.next_payload()).data == "one"
    assert (await mixed.next_payload()).data == "two"


async def run_async_edges() -> bool:
    await body_chunk_cases()
    await low_level_cases()
    await retry_and_adapter_cases()
    await sse_cases()
    return True
