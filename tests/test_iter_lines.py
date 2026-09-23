from __future__ import annotations

import asyncio
import gc
import random
import weakref
from types import SimpleNamespace

import pytest

from niquests import AsyncResponse, Response
from niquests.exceptions import StreamConsumedError
from niquests.models import _LineDecoder

pytestmark = pytest.mark.asyncio


class ChunkResponse(Response):
    def __init__(self, chunks):
        super().__init__()
        self.chunks = chunks
        self.calls = []
        self.pulled = 0

    def iter_content(self, chunk_size=-1, decode_unicode=False):
        self.calls.append((chunk_size, decode_unicode))

        def generate():
            for chunk in self.chunks:
                self.pulled += 1
                if isinstance(chunk, BaseException):
                    raise chunk
                yield chunk

        return generate()


class AsyncChunkResponse(ChunkResponse, AsyncResponse):
    async def iter_content(self, chunk_size=-1, decode_unicode=False):
        chunks = super().iter_content(chunk_size, decode_unicode)

        async def generate():
            for chunk in chunks:
                if isinstance(chunk, asyncio.Event):
                    chunk.set()
                    await asyncio.Future()
                else:
                    yield chunk

        return generate()


@pytest.fixture(params=[ChunkResponse, AsyncChunkResponse], ids=["sync", "async"])
def source(request):
    return request.param


async def collect(response, **kwargs):
    lines = response.iter_lines(**kwargs)
    return [line async for line in lines] if isinstance(response, AsyncResponse) else list(lines)


async def take(lines):
    if hasattr(lines, "__anext__"):
        try:
            return await lines.__anext__()
        except StopAsyncIteration:
            return None
    return next(lines, None)


def old_chunk_parser(chunks, delimiter):
    """The pre-optimization parser, deliberately not whole-body split()."""
    pending = None
    for chunk in chunks:
        if pending is not None:
            chunk = pending + chunk
        lines = chunk.split(delimiter) if delimiter else chunk.splitlines()
        if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
            pending = lines.pop()
        else:
            pending = None
        yield from lines
    if pending is not None:
        yield pending


@pytest.mark.parametrize("text", [False, True], ids=["bytes", "str"])
async def test_chunk_specific_examples(source, text):
    cases = [
        ([], None, []),
        ([""], None, []),
        (["a\r", "\nb"], None, ["a", "", "b"]),
        (["a\r", "\nb"], "\r\n", ["a", "b"]),
        (["a\nb\r", "\nc"], "", ["a", "b", "", "c"]),
        (["a\n", "b"], "\n", ["a", "", "b"]),
        (["", "", "a", "", "b", "::", ""], "::", ["", "", "ab", "", ""]),
        (["ab", "", "cd"], None, ["abcd"]),
        (list("aaaaa"), "aa", ["", "", "", "", "a"]),
        (list("abababa"), "aba", ["", "", "b", ""]),
        (list("x::::y::z"), "::", ["x", "", "", "", "y", "", "z"]),
        (["x::::y::z"], "::", ["x", "", "y", "z"]),
        (list("xababacayababacaz"), "ababaca", ["x", "", "y", "", "z"]),
        (["a\r\nb\rc\n"], None, ["a", "b", "c"]),
    ]
    if text:
        cases.append((["a\v", "b\f", "c\x1c", "d\x85", "e\u2028", "f\u2029"], None, list("abcdef")))
    for chunks, delimiter, expected in cases:
        if not text:
            chunks = [chunk.encode() for chunk in chunks]
            delimiter = delimiter.encode() if delimiter is not None else None
            expected = [line.encode() for line in expected]
        assert await collect(source(chunks), delimiter=delimiter, decode_unicode=text) == expected, (chunks, delimiter)


@pytest.mark.parametrize("text", [False, True], ids=["bytes", "str"])
async def test_seeded_differential(source, text):
    rng = random.Random(71293)
    for separator in (None, "", "\n", "\r\n", "::", "aa", "aba", "ababaca", "\u2028"):
        delimiter = separator if text or separator is None else separator.encode()
        for _ in range(60):
            body = "".join(rng.choices("aaabb::\r\n\v\f\x1c\x85\u2028\u2029", k=rng.randrange(100)))
            if rng.randrange(2):
                body = "x\u20ac" * rng.randrange(150, 350) + body
            body = body if text else body.encode()
            chunks, offset = [], 0
            while offset < len(body):
                if rng.randrange(3) == 0:
                    chunks.append(body[:0])
                width = rng.randrange(1, 8)
                chunks.append(body[offset : offset + width])
                offset += width
            chunks.extend([body[:0]] * rng.randrange(3))
            expected = list(old_chunk_parser(chunks, delimiter))
            assert await collect(source(chunks), delimiter=delimiter, decode_unicode=text) == expected, (chunks, delimiter)


async def test_no_lookahead_and_immediate_empty_record(source):
    response = source([b"a::", b"b::", b"tail"])
    lines = response.iter_lines(chunk_size=7, delimiter=b"::")
    assert response.calls == [] and response.pulled == 0
    for expected, pulled in [(b"a", 1), (b"", 1), (b"b", 2), (b"", 2), (b"tail", 3)]:
        assert await take(lines) == expected
        assert response.pulled == pulled
    assert await take(lines) is None
    assert response.calls == [(7, False)]


async def test_type_validation_is_lazy_and_native(source):
    assert await collect(source(["a\n", "b"]), delimiter=b"", decode_unicode=True) == ["a", "b"]
    for delimiter in ("", "::"):
        response = source([b"never read"])
        lines = response.iter_lines(delimiter=delimiter)
        with pytest.raises(ValueError, match="delimiter MUST match"):
            await take(lines)
        assert response.calls == [] and response.pulled == 0
    for chunk, delimiter in [(b"", "::"), (b"x", "::"), ("", b"::"), ("x", b"::"), (b"x", 1)]:
        assert await collect(source([]), delimiter=delimiter, decode_unicode=True) == []
        with pytest.raises(TypeError) as native:
            chunk.split(delimiter)
        response = source([chunk, chunk])
        with pytest.raises(TypeError) as actual:
            await take(response.iter_lines(delimiter=delimiter, decode_unicode=True))
        assert str(actual.value) == str(native.value)
        assert response.pulled == 1


@pytest.mark.parametrize("delimiter", [None, b"::"])
async def test_error_and_early_close_do_not_flush_pending(source, delimiter):
    separator = delimiter or b"\n"
    response = source([b"ready" + separator + b"pending", b"never read"])
    lines = response.iter_lines(delimiter=delimiter)
    assert await take(lines) == b"ready"
    if isinstance(response, AsyncResponse):
        await lines.aclose()
    else:
        lines.close()
    assert await take(lines) is None and response.pulled == 1

    error = RuntimeError("source failed")
    response = source([b"pending", b"more", error, b"never read"])
    lines = response.iter_lines(delimiter=delimiter)
    with pytest.raises(RuntimeError) as caught:
        await take(lines)
    assert caught.value is error
    assert await take(lines) is None and response.pulled == 3


@pytest.mark.parametrize("delimiter", [None, b"aba"])
async def test_async_cancellation_does_not_flush_pending(delimiter):
    blocked = asyncio.Event()
    response = AsyncChunkResponse([b"pending", b"more", blocked, b"never read"])
    lines = response.iter_lines(delimiter=delimiter)
    task = asyncio.create_task(lines.__anext__())
    try:
        await asyncio.wait_for(blocked.wait(), timeout=5)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await lines.aclose()
    assert await take(lines) is None and response.pulled == 3


@pytest.mark.parametrize("text", [False, True], ids=["bytes", "str"])
async def test_long_fragmented_record(source, text):
    for delimiter in (None, "aba"):
        for terminated in (False, True):
            actual_delimiter = delimiter
            fragment = "x" * 31
            chunks = [fragment] * 8192
            if terminated:
                chunks.extend(list(delimiter or "\n"))
            expected = [fragment * 8192] + ([""] if terminated and delimiter else [])
            if not text:
                chunks = [chunk.encode() for chunk in chunks]
                expected = [line.encode() for line in expected]
                actual_delimiter = delimiter.encode() if delimiter is not None else None
            assert await collect(source(chunks), delimiter=actual_delimiter, decode_unicode=text) == expected


@pytest.mark.parametrize("delimiter", [None, b"::"])
async def test_long_record_then_short_records(source, delimiter):
    separator = delimiter or b"\n"
    chunks = [b"x" * 32] * 128 + [separator + b"a" + separator + b"b", separator + b"c" + separator, b"d"]
    expected = [b"x" * 4096, b"a", b"b", b"c"] + ([b""] if delimiter else []) + [b"d"]
    assert await collect(source(chunks), delimiter=delimiter) == expected


@pytest.mark.parametrize("delimiter", [None, b"\n", b"::", "\n", "::"])
@pytest.mark.parametrize("at_eof", [False, True])
async def test_decoder_releases_fragments(delimiter, at_eof):
    fragment = "x" * 32 if isinstance(delimiter, str) else b"x" * 32
    decoder = _LineDecoder(delimiter)
    for _ in range(32):
        assert decoder.decode(fragment) == []
    if at_eof:
        assert decoder.flush() == fragment * 32
    else:
        assert decoder.decode(delimiter or b"\n") == [fragment * 32] + ([fragment[:0]] if delimiter else [])
    assert not decoder.buffer and decoder.tail is None
    assert decoder.flush() is None


@pytest.mark.parametrize("delimiter", [None, b"::"])
async def test_fragmented_record_work_is_linear(source, delimiter):
    work = {"copied": 0, "scanned": 0}

    class MeasuredBytes(bytes):
        def __add__(self, other):
            work["copied"] += len(self) + len(other)
            return MeasuredBytes(super().__add__(other))

        def __getitem__(self, key):
            value = super().__getitem__(key)
            return MeasuredBytes(value) if isinstance(key, slice) else value

        def split(self, sep):
            work["scanned"] += len(self)
            return [MeasuredBytes(part) for part in super().split(sep)]

        def splitlines(self):
            work["scanned"] += len(self)
            return [MeasuredBytes(part) for part in super().splitlines()]

        def join(self, parts):
            work["copied"] += sum(map(len, parts))
            return MeasuredBytes(super().join(parts))

    chunks = [MeasuredBytes(b"x" * 31)] * 512
    assert await collect(source(chunks), delimiter=delimiter) == [b"x" * (31 * 512)]
    assert work["copied"] < 4 * 31 * 512
    assert work["scanned"] < 2 * 31 * 512


async def test_emitted_long_record_is_released(source):
    retained = []

    class Marker:
        pass

    class TrackedBytes(bytes):
        def __add__(self, other):
            return TrackedBytes(super().__add__(other))

        def splitlines(self):
            parts = [TrackedBytes(part) for part in super().splitlines()]
            for part in parts:
                if len(part) >= 65536:
                    part.marker = Marker()
                    retained.append(weakref.ref(part.marker))
            return parts

    response = source([TrackedBytes(b"x" * 65536), b"x", b"\n", b"ok\n", b"more\n"])
    lines = response.iter_lines()
    line = await take(lines)
    assert line == b"x" * 65536 + b"x"
    del line
    assert await take(lines) == b"ok"
    gc.collect()
    assert retained and all(reference() is None for reference in retained)
    assert await take(lines) == b"more"

    retained.clear()
    response = source([TrackedBytes(b"x" * 65536), b"x", b"x"])
    lines = response.iter_lines()
    assert await take(lines) == b"x" * 65536 + b"xx"
    gc.collect()
    assert retained and all(reference() is None for reference in retained)
    assert await take(lines) is None


@pytest.mark.parametrize("backend", ["stream", "read", "async"])
@pytest.mark.parametrize("encoding", [None, "utf-8"])
async def test_real_iter_content_decoding_state_trailers_and_gather(backend, encoding):
    response = AsyncResponse() if backend == "async" else Response()
    response.encoding = encoding
    chunks = iter([b"\xe2", b"\x82", b"\xac::", b"tail", b"\xe2"])
    gathered = []

    def read(size, decode_content=True):
        assert size == 3 and decode_content is True
        return next(chunks, b"")

    async def async_read(size, decode_content=True):
        return read(size, decode_content)

    def stream(size, decode_content):
        assert size == 3 and decode_content is True
        yield from chunks

    raw = SimpleNamespace(trailers={"X-End": "yes"})
    if backend == "stream":
        raw.stream = stream
    else:
        raw.read = async_read if backend == "async" else read
    if backend == "async":

        async def gather(result):
            assert result is response
            gathered.append(result)
            result.raw = raw
            del result._promise

        response._promise = object()
        response.connection = SimpleNamespace(gather=gather)
    else:
        response.raw = raw
    delimiter = "::" if encoding else b"::"
    lines = response.iter_lines(chunk_size=3, delimiter=delimiter, decode_unicode=True)
    if backend == "async":
        assert not gathered
        assert response.lazy
    assert await take(lines) == ("\u20ac" if encoding else b"\xe2\x82\xac")
    assert not response._content_consumed and not response.trailers
    assert await take(lines) == ("" if encoding else b"")
    assert await take(lines) == ("tail\ufffd" if encoding else b"tail\xe2")
    assert await take(lines) is None
    assert response._content_consumed and response.trailers["x-end"] == "yes"
    with pytest.raises(StreamConsumedError):
        await collect(response)
    if backend == "async":
        assert gathered == [response]
        assert not response.lazy


async def test_sync_cached_content_keeps_chunk_boundaries():
    response = Response()
    response._content, response._content_consumed = b"a\r\nb", True
    assert await collect(response, chunk_size=2) == [b"a", b"", b"b"]
    assert await collect(response, chunk_size=2, delimiter=b"\r\n") == [b"a", b"b"]
