from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from componentize_py_types import Err, Ok
from niquests.packages.urllib3._collections import HTTPHeaderDict
from niquests.packages.urllib3.util.retry import Retry

import niquests.extensions.wasi._adapter as wasi
import niquests.extensions.wasi._utils as common
from niquests.exceptions import ConnectionError, ConnectTimeout, InvalidSchema, InvalidURL, ReadTimeout, SSLError
from niquests.models import PreparedRequest, Response


class Resource:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True


class Pollable(Resource):
    def block(self):
        pass


class Closed:
    pass


class Failed:
    pass


class Stream(Resource):
    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def read(self, amount):
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def subscribe(self):
        return Pollable()


class Future(Resource):
    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def get(self):
        return self.values.pop(0)

    def subscribe(self):
        return Pollable()


class Trailer(Resource):
    def entries(self):
        return [("x-trailer", b"done")]


class Body(Resource):
    pass


class IncomingBody:
    future = Future([Ok(Ok(None))])

    @classmethod
    def finish(cls, body):
        body.closed = True
        return cls.future


class BrokenIncomingBody:
    @staticmethod
    def finish(body):
        raise Err(Failed())


class UnexpectedIncomingBody:
    @staticmethod
    def finish(body):
        raise ValueError("unexpected")


class Options:
    def __init__(self, fail=False):
        self.values = []
        self.fail = fail

    def _set(self, value):
        if self.fail:
            raise ValueError
        self.values.append(value)

    set_connect_timeout = set_first_byte_timeout = set_between_bytes_timeout = _set


class Variants:
    @staticmethod
    def Method_Get():
        return "get"

    @staticmethod
    def Method_Other(value):
        return value

    @staticmethod
    def Scheme_Http():
        return "http"

    @staticmethod
    def Scheme_Https():
        return "https"


class Raw:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    def read(self, amount):
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True


class Output(Resource):
    fail = False

    def blocking_write_and_flush(self, value):
        if self.fail:
            raise Err(Failed())


class OutgoingBody:
    def write(self):
        return Output()


class OutgoingRequest:
    def __init__(self, fields):
        pass

    def set_method(self, value):
        pass

    def set_scheme(self, value):
        pass

    def set_authority(self, value):
        pass

    def set_path_with_query(self, value):
        pass

    def body(self):
        return OutgoingBody()


class Fields(Resource):
    @classmethod
    def from_list(cls, values):
        return cls()


class FakeOptions(Options):
    pass


class GoodBody(Body):
    def stream(self):
        return Stream([Err(Closed())])


class Headers(Resource):
    def entries(self):
        return []


class GoodIncoming:
    def status(self):
        return 200

    def headers(self):
        return Headers()

    def consume(self):
        return GoodBody()


class BadIncoming(GoodIncoming):
    def consume(self):
        raise Err(Failed())


class FakeTypes:
    Fields = Fields
    OutgoingRequest = OutgoingRequest
    RequestOptions = FakeOptions
    IncomingBody = IncomingBody
    OutgoingBody = SimpleNamespace(finish=lambda body, trailers: None)

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


def prepared(url="https://example.test", method="GET"):
    request = PreparedRequest()
    request.prepare(method=method, url=url)
    return request


def test_common_branches():
    assert common.validate_transport_options(prepared("psse://example.test/x?q=1"), True, None, None) == (
        "http",
        "example.test",
        "/x?q=1",
    )
    with pytest.raises(InvalidSchema):
        common.validate_transport_options(prepared("ftp://example.test"), True, None, None)
    missing = PreparedRequest()
    missing.url = "https:///missing"
    with pytest.raises(InvalidURL):
        common.validate_transport_options(missing, True, None, None)
    with pytest.raises(SSLError):
        common.validate_transport_options(prepared(), "/ca.pem", None, None)
    with pytest.raises(SSLError):
        common.validate_transport_options(prepared(), True, "cert.pem", None)
    with pytest.raises(ConnectionError, match="WASI HTTP WIT bindings do not expose proxy support"):
        common.validate_transport_options(prepared(), True, None, {"https": "http://proxy.test"})

    request = prepared()
    request.headers = {b"X-Test": b"value", "Host": "ignored"}
    headers = common.request_headers(request, sse=True)
    assert ("X-Test", b"value") in headers
    assert ("Accept", b"text/event-stream") in headers
    request.headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-store",
        "Accept-Encoding": "identity",
    }
    assert len(common.request_headers(request, sse=True)) == 3
    assert ("Accept-Encoding", b"identity") in common.request_headers(request)
    request.headers = {}
    assert common.request_headers(request) == []

    response_headers = common.response_headers([("X", b"a"), ("x", b"b")])
    assert response_headers["x"] == "a, b"
    assert common.method_variant(Variants, "GET") == "get"
    assert common.method_variant(Variants, "CUSTOM") == "CUSTOM"
    assert common.scheme_variant(Variants, "http") == "http"
    assert common.scheme_variant(Variants, "https") == "https"

    for payload, expected in (
        (type("TLSCertificateError", (), {})(), SSLError),
        (type("DNSTimeout", (), {})(), ConnectTimeout),
        (type("ConnectionReadTimeout", (), {})(), ReadTimeout),
        (type("OtherFailure", (), {})(), ConnectionError),
    ):
        with pytest.raises(expected):
            with common.wasi_exception_mapping("https://example.test"):
                raise Err(payload)
    with pytest.raises(ReadTimeout):
        with common.wasi_exception_mapping("https://example.test", reading=True):
            raise Err(Failed())

    common.close_resource(None)
    common.close_resource(object())
    resource = Resource()
    common.close_resource(resource)
    assert resource.closed

    assert common.timeout_values(None) == (None, None)
    assert common.timeout_values(()) == (None, None)
    assert common.timeout_values((1,)) == (1, 1)
    assert common.timeout_values((1, 2, 3)) == (1, 2)
    assert common.timeout_values((1, None, 3)) == (1, 3)
    timeout = SimpleNamespace(connect_timeout=1, read_timeout=2, total=3)
    assert common.timeout_values(timeout) == (1, 2)
    assert common.timeout_values(4) == (4, 4)
    options = Options()
    common.set_timeouts(options, (1, 2))
    assert len(options.values) == 3
    with pytest.raises(ValueError):
        common.set_timeouts(Options(fail=True), (1, 2))
    common.set_timeouts(Options(), (None, 2))
    common.set_timeouts(Options(), (1, None))


def test_sse_parser_branches():
    raw = Raw([b": comment\r\n\r\nid: 1\r\nretry: nope\r\ndata: one\r\n\r\ndata: two\r\n\r\n"])
    extension = wasi.WASISSEExtension(raw)
    assert "id: 1" in extension.next_payload(raw=True)
    assert extension.next_payload().id == "1"
    assert extension.next_payload() is None
    assert extension.closed
    extension.close()
    with pytest.raises(OSError):
        extension.next_payload()
    with pytest.raises(NotImplementedError):
        extension.start(None)
    other = wasi.WASISSEExtension(Raw([b"id: bad\0id\nretry: 10\nevent: ping\ndata:no-space\n\n"]))
    assert other.next_payload().retry == 10
    other.close()
    mixed = wasi.WASISSEExtension(Raw([b"data: one\r\n\r\ndata: two\n\n"]))
    assert mixed.next_payload().data == "one"
    assert mixed.next_payload().data == "two"


def test_low_level_read_finish_abort_and_errors():
    original = (wasi._TYPES, wasi._Ok, wasi._Err, wasi._StreamErrorClosed)
    wasi._TYPES = SimpleNamespace(IncomingBody=IncomingBody)
    wasi._Ok = Ok
    wasi._Err = Err
    wasi._StreamErrorClosed = Closed
    future = Future([None, Ok(Ok(Trailer()))])
    IncomingBody.future = future
    low = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([b"", b"x", Err(Closed())]), "url")
    assert low.read(1) == b"x"
    assert low.read(1) == b""
    assert low.trailers["x-trailer"] == "done"
    assert future.closed

    failed = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([Err(Failed())]), "url")
    with pytest.raises(ReadTimeout):
        failed.read(1)
    unexpected_read = wasi._WASILowLevelResponse(
        "GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([ValueError("unexpected")]), "url"
    )
    with pytest.raises(ValueError):
        unexpected_read.read(1)

    wasi._TYPES = SimpleNamespace(IncomingBody=BrokenIncomingBody)
    broken = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([Err(Closed())]), "url")
    with pytest.raises(ReadTimeout):
        broken.read(1)
    wasi._TYPES = SimpleNamespace(IncomingBody=UnexpectedIncomingBody)
    unexpected_finish = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([Err(Closed())]), "url")
    with pytest.raises(ValueError):
        unexpected_finish.read(1)

    wasi._TYPES = SimpleNamespace(IncomingBody=IncomingBody)
    IncomingBody.future = Future([Ok(Ok(None))])
    no_body = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), None, Stream([Err(Closed())]), "url")
    assert no_body.read(1) == b""

    IncomingBody.future = Future([Ok(Ok(None))])
    cancellable = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([b"pending"]), "url")
    response = wasi._WASIHTTPResponse(body=cancellable, headers={}, preload_content=False)
    response.close()
    response.close()
    assert cancellable.closed and cancellable._stream is None
    wasi._WASIHTTPResponse(body=b"done").close()

    no_body_abort = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), None, Stream([b"pending"]), "url")
    no_body_abort.abort()
    wasi._TYPES = SimpleNamespace(IncomingBody=BrokenIncomingBody)
    error_abort = wasi._WASILowLevelResponse("GET", 200, "OK", HTTPHeaderDict(), Body(), Stream([b"pending"]), "url")
    error_abort.abort()
    wasi._TYPES, wasi._Ok, wasi._Err, wasi._StreamErrorClosed = original


def test_unwrap_repr_and_close():
    original = (wasi._Ok, wasi._Err)
    wasi._Ok = Ok
    wasi._Err = Err
    with pytest.raises(Err):
        wasi._unwrap(Err(Failed()))
    assert wasi._unwrap(Ok("ok")) == "ok"
    assert wasi._unwrap("raw") == "raw"
    wasi._Ok, wasi._Err = original
    adapter = wasi.WASIAdapter()
    assert repr(adapter) == "<WASIAdapter HTTP/0.2>"
    adapter.close()


def test_transport_retry_and_status_exhaustion_branches():
    attempts = 0
    adapter = wasi.WASIAdapter(max_retries=Retry(total=1, connect=1))

    def send_once(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("retry")
        response = Response()
        response.status_code = 200
        response.headers = {}
        response.raw = Raw([])
        return response

    adapter._send_once = send_once
    assert adapter.send(prepared()).status_code == 200
    assert attempts == 2

    attempts = 0
    payloads = []
    body_request = PreparedRequest()
    body_request.prepare(method="PUT", url="https://example.test", data=BytesIO(b"payload"))

    def send_body_once(request, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        payloads.append(request.body.read())
        if attempts == 1:
            raise ConnectionError("retry")
        response = Response()
        response.status_code = 200
        response.headers = {}
        response.raw = Raw([])
        return response

    adapter._send_once = send_body_once
    assert adapter.send(body_request).status_code == 200
    assert payloads == [b"payload", b"payload"]

    exhausted = wasi.WASIAdapter(max_retries=Retry(total=0, status=0, status_forcelist={500}, raise_on_status=False))

    def status_once(*args, **kwargs):
        response = Response()
        response.status_code = 500
        response.headers = {}
        response.raw = Raw([])
        return response

    exhausted._send_once = status_once
    assert exhausted.send(prepared()).status_code == 500
