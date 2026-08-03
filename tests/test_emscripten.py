"""This module is horrific so far, I had to speed up the writing of this module to gain the
absolute minimal confidence that our WASM support isn't completely broken.
Each test is split into two functions to retrieve run_in_pyodide output(...) especially
the coverage aspect!
"""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture(
    # Pickleable HTTP, WebSocket, and SSE origins passed into Pyodide.
    params=[
        pytest.param(
            ("http://localhost:8888", "ws://localhost:8888", "psse://localhost:8888"),
            id="local",
        ),
        pytest.param(
            ("https://httpbingo.org", "wss://httpbingo.org", "sse://httpbingo.org"),
            id="live",
        ),
    ]
)
def httpbin_target(request):
    request.getfixturevalue("requires_traefik_http" if request.param[0].startswith("http://") else "requires_wan")
    return request.param


# Handle the import safely. If pytest-pyodide is not installed (e.g. checks in IDE),
# we define a dummy decorator and mock fixtures to avoid NameError/fixture errors.
try:
    from pytest_pyodide import run_in_pyodide
except ImportError:

    def run_in_pyodide(*args, **kwargs):
        def decorator(func):
            return pytest.mark.skip(reason="pytest-pyodide not installed")(func)

        return decorator

    @pytest.fixture
    def selenium():
        pytest.skip("pytest-pyodide not installed")

    @pytest.fixture
    def selenium_jspi():
        pytest.skip("pytest-pyodide not installed")


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_basic_get(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[0]}/get")
            assert response.status_code == 200
            assert "headers" in response.json()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_basic_get(selenium_jspi, httpbin_target):
    """Test basic GET request works."""
    data = _inner_test_sync_basic_get(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_basic_post(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.post(f"{httpbin_target[0]}/post", json={"test": "data"})
            assert response.status_code == 200
            data = response.json()
            assert data["json"] == {"test": "data"}
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_basic_post(selenium_jspi, httpbin_target):
    """Test basic POST request works."""
    data = _inner_test_sync_basic_post(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_streaming_read(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[0]}/stream/5", stream=True)
            assert response.status_code == 200

            chunks = []
            for chunk in response.iter_lines():
                if chunk:
                    chunks.append(chunk)

            assert len(chunks) == 5
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_streaming_read(selenium_jspi, httpbin_target):
    """Test streaming response works."""
    data = _inner_test_sync_streaming_read(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_retry_works(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session(retries=3) as s:
            response = s.get(f"{httpbin_target[0]}/get")
            assert response.status_code == 200
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_retry_works(selenium_jspi, httpbin_target):
    """Test that retry mechanism works."""
    data = _inner_test_sync_retry_works(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_basic_get(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[0]}/get")
            assert response.status_code == 200
            assert "headers" in response.json()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_basic_get(selenium, httpbin_target):
    """Test basic async GET request works."""
    data = _inner_test_async_basic_get(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_basic_post(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.post(f"{httpbin_target[0]}/post", json={"test": "data"})
            assert response.status_code == 200
            data = response.json()
            assert data["json"] == {"test": "data"}
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_basic_post(selenium, httpbin_target):
    """Test basic async POST request works."""
    data = _inner_test_async_basic_post(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_streaming_read(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[0]}/stream/5", stream=True)
            assert response.status_code == 200

            chunks = []
            async for chunk in response.iter_lines():
                if chunk:
                    chunks.append(chunk)

            assert len(chunks) == 5
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_streaming_read(selenium, httpbin_target):
    """Test async streaming response works."""
    data = _inner_test_async_streaming_read(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_retry_works(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession(retries=3) as s:
            response = await s.get(f"{httpbin_target[0]}/get")
            assert response.status_code == 200
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_retry_works(selenium, httpbin_target):
    """Test that async retry mechanism works."""
    data = _inner_test_async_retry_works(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_websocket(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import sys

    if "emscripten" not in sys.platform:
        return b""

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[1]}/websocket/echo")
            assert response.status_code == 101

            ext = response.extension
            assert ext is not None
            assert ext.closed is False

            ext.send_payload("hello from niquests")
            msg = ext.next_payload()
            assert isinstance(msg, str)
            assert msg == "hello from niquests"

            ext.close()
            assert ext.closed is True
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_websocket(selenium_jspi, httpbin_target):
    """Test sync WebSocket via browser native API + JSPI."""
    data = _inner_test_sync_websocket(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_websocket_binary(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[1]}/websocket/echo")
            assert response.status_code == 101

            ext = response.extension

            ext.send_payload(b"\x00\x01\x02\x03")
            msg = ext.next_payload()
            assert isinstance(msg, bytes)
            assert msg == b"\x00\x01\x02\x03"

            ext.close()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_websocket_binary(selenium_jspi, httpbin_target):
    """Test sync WebSocket binary message handling."""
    data = _inner_test_sync_websocket_binary(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_websocket_close_from_server(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[1]}/websocket/echo")
            ext = response.extension
            assert ext.closed is False

            # Close from our side, then verify state
            ext.close()
            assert ext.closed is True
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_websocket_close_from_server(selenium_jspi, httpbin_target):
    """Test that close works and state is updated."""
    data = _inner_test_sync_websocket_close_from_server(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_websocket(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[1]}/websocket/echo")
            assert response.status_code == 101

            ext = response.extension
            assert ext is not None
            assert ext.closed is False

            await ext.send_payload("hello from niquests async")
            msg = await ext.next_payload()
            assert isinstance(msg, str)
            assert msg == "hello from niquests async"

            await ext.close()
            assert ext.closed is True
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_websocket(selenium, httpbin_target):
    """Test async WebSocket via browser native API."""
    data = _inner_test_async_websocket(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_websocket_binary(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[1]}/websocket/echo")
            assert response.status_code == 101

            ext = response.extension

            await ext.send_payload(b"\x00\x01\x02\x03")
            msg = await ext.next_payload()
            assert isinstance(msg, bytes)
            assert msg == b"\x00\x01\x02\x03"

            await ext.close()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_websocket_binary(selenium, httpbin_target):
    """Test async WebSocket binary message handling."""
    data = _inner_test_async_websocket_binary(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_sse(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent

        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[2]}/sse?count=3&duration=1")
            assert response.status_code == 200

            ext = response.extension
            assert ext is not None
            assert ext.closed is False

            events = []
            while True:
                event = ext.next_payload()
                if event is None:
                    break
                assert isinstance(event, ServerSentEvent)
                events.append(event)

            assert len(events) >= 1
            assert ext.closed is True
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_sse(selenium_jspi, httpbin_target):
    """Test sync SSE via pyfetch streaming + manual parsing."""
    data = _inner_test_sync_sse(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_sse(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent

        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[2]}/sse?count=3&duration=1")
            assert response.status_code == 200

            ext = response.extension
            assert ext is not None
            assert ext.closed is False

            events = []
            while True:
                event = await ext.next_payload()
                if event is None:
                    break
                assert isinstance(event, ServerSentEvent)
                events.append(event)

            assert len(events) >= 1
            assert ext.closed is True
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_sse(selenium, httpbin_target):
    """Test async SSE via pyfetch streaming + manual parsing."""
    data = _inner_test_async_sse(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_sse_send_raises(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import pytest

        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[2]}/sse?count=1&duration=1")
            ext = response.extension

            with pytest.raises(NotImplementedError):
                ext.send_payload("test")

            ext.close()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_sse_send_raises(selenium_jspi, httpbin_target):
    """Test that SSE send_payload raises NotImplementedError."""
    data = _inner_test_sync_sse_send_raises(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_timeout(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import pytest
        from niquests.packages.urllib3.exceptions import MaxRetryError

        from niquests import Session, TimeoutConfiguration
        from niquests.exceptions import ConnectTimeout

        with Session(retries=False) as s:
            with pytest.raises(ConnectTimeout):
                s.get(f"{httpbin_target[0]}/delay/5", timeout=0.5)

        with Session(retries=0) as s:
            with pytest.raises(MaxRetryError):
                s.get(f"{httpbin_target[0]}/delay/5", timeout=0.5)

        with Session(retries=0) as s:
            with pytest.raises(MaxRetryError):
                s.get(f"{httpbin_target[0]}/delay/5", timeout=TimeoutConfiguration(0.5))
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_timeout(selenium_jspi, httpbin_target):
    """Test that timeout raises ConnectTimeout on slow responses."""
    data = _inner_test_sync_timeout(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_timeout(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import pytest
        from niquests.packages.urllib3.exceptions import MaxRetryError

        from niquests import AsyncSession, TimeoutConfiguration
        from niquests.exceptions import ConnectTimeout

        async with AsyncSession(retries=False) as s:
            with pytest.raises(ConnectTimeout):
                await s.get(f"{httpbin_target[0]}/delay/5", timeout=0.5)

        async with AsyncSession(retries=0) as s:
            with pytest.raises(MaxRetryError):
                await s.get(f"{httpbin_target[0]}/delay/5", timeout=0.5)

        async with AsyncSession(retries=0) as s:
            with pytest.raises(MaxRetryError):
                await s.get(f"{httpbin_target[0]}/delay/5", timeout=TimeoutConfiguration(0.5))
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_timeout(selenium, httpbin_target):
    """Test that async timeout raises ConnectTimeout on slow responses."""
    data = _inner_test_async_timeout(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_custom_request_headers(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(
                f"{httpbin_target[0]}/headers",
                headers={"X-Custom-Test": "niquests-pyodide", "Accept": "application/json"},
            )
            assert response.status_code == 200

            data = response.json()
            # httpbingo returns the received headers
            headers = data.get("headers", {})
            assert "X-Custom-Test" in headers
            assert headers["X-Custom-Test"] == ["niquests-pyodide"]

            # Verify response headers are accessible
            assert "content-type" in response.headers
            assert "application/json" in response.headers["content-type"]
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_custom_request_headers(selenium_jspi, httpbin_target):
    """Test that custom request headers are sent and response headers are parsed."""
    data = _inner_test_sync_custom_request_headers(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_custom_request_headers(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(
                f"{httpbin_target[0]}/headers",
                headers={"X-Custom-Test": "niquests-pyodide", "Accept": "application/json"},
            )
            assert response.status_code == 200

            data = response.json()
            headers = data.get("headers", {})
            assert "X-Custom-Test" in headers
            assert headers["X-Custom-Test"] == ["niquests-pyodide"]

            assert "content-type" in response.headers
            assert "application/json" in response.headers["content-type"]
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_custom_request_headers(selenium, httpbin_target):
    """Test that async custom request headers are sent and response headers are parsed."""
    data = _inner_test_async_custom_request_headers(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_forbidden_header_silently_dropped(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(
                f"{httpbin_target[0]}/headers",
                headers={"Host": "evil.example.com", "Connection": "close", "X-Legit": "present"},
            )
            assert response.status_code == 200

            data = response.json()
            headers = data.get("headers", {})

            # The forbidden headers must NOT reach the server
            assert headers.get("Host", [None])[0] != "evil.example.com"
            assert headers.get("Connection", [""])[0] != "close"

            # Non-forbidden headers must still be sent
            assert "X-Legit" in headers
            assert headers["X-Legit"] == ["present"]
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_forbidden_header_silently_dropped(selenium_jspi, httpbin_target):
    """Test that forbidden headers (e.g. Host) are silently stripped and do not cause errors."""
    data = _inner_test_sync_forbidden_header_silently_dropped(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_forbidden_header_silently_dropped(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(
                f"{httpbin_target[0]}/headers",
                headers={"Host": "evil.example.com", "Connection": "close", "X-Legit": "present"},
            )
            assert response.status_code == 200

            data = response.json()
            headers = data.get("headers", {})

            # The forbidden headers must NOT reach the server
            assert headers.get("Host", [None])[0] != "evil.example.com"
            assert headers.get("Connection", [""])[0] != "close"

            # Non-forbidden headers must still be sent
            assert "X-Legit" in headers
            assert headers["X-Legit"] == ["present"]
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_forbidden_header_silently_dropped(selenium, httpbin_target):
    """Test that forbidden headers (e.g. Host) are silently stripped and do not cause errors (async)."""
    data = _inner_test_async_forbidden_header_silently_dropped(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_non_ok_response(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import pytest

        from niquests import Session
        from niquests.exceptions import HTTPError

        with Session() as s:
            response = s.get(f"{httpbin_target[0]}/status/418")
            assert response.status_code == 418
            assert response.ok is False

            with pytest.raises(HTTPError, match="418"):
                response.raise_for_status()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_non_ok_response(selenium_jspi, httpbin_target):
    """Test non-OK responses and raise_for_status."""
    data = _inner_test_sync_non_ok_response(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_non_ok_response(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import pytest

        from niquests import AsyncSession
        from niquests.exceptions import HTTPError

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[0]}/status/418")
            assert response.status_code == 418
            assert response.ok is False

            with pytest.raises(HTTPError, match="418"):
                response.raise_for_status()
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_non_ok_response(selenium, httpbin_target):
    """Test async non-OK responses and raise_for_status."""
    data = _inner_test_async_non_ok_response(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_binary_response(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[0]}/image/jpeg")
            assert response.status_code == 200
            assert "image/jpeg" in response.headers.get("content-type", "")

            # JPEG files start with FF D8
            assert isinstance(response.content, bytes)
            assert len(response.content) > 100
            assert response.content[:2] == b"\xff\xd8"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_binary_response(selenium_jspi, httpbin_target):
    """Test binary response content (JPEG image)."""
    data = _inner_test_sync_binary_response(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_binary_response(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[0]}/image/jpeg")
            assert response.status_code == 200
            assert "image/jpeg" in response.headers.get("content-type", "")

            assert isinstance(response.content, bytes)
            assert len(response.content) > 100
            assert response.content[:2] == b"\xff\xd8"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_binary_response(selenium, httpbin_target):
    """Test async binary response content (JPEG image)."""
    data = _inner_test_async_binary_response(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_redirect(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[0]}/redirect/3")
            assert response.status_code == 200
            # After 3 redirects, we should end up at /get
            assert response.url.endswith("/get") or "/get" in response.url
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_redirect(selenium_jspi, httpbin_target):
    """Test that redirects are followed and final URL is correct."""
    data = _inner_test_sync_redirect(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_redirect(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[0]}/redirect/3")
            assert response.status_code == 200
            assert response.url.endswith("/get") or "/get" in response.url
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_redirect(selenium, httpbin_target):
    """Test that async redirects are followed and final URL is correct."""
    data = _inner_test_async_redirect(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_string_body(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.post(
                f"{httpbin_target[0]}/post",
                data="raw string body",
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data") == "raw string body"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_string_body(selenium_jspi, httpbin_target):
    """Test POST with a raw string body."""
    data = _inner_test_sync_string_body(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_string_body(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.post(
                f"{httpbin_target[0]}/post",
                data="raw string body",
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data") == "raw string body"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_string_body(selenium, httpbin_target):
    """Test async POST with a raw string body."""
    data = _inner_test_async_string_body(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_iterable_body(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        def body_gen():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        with Session() as s:
            response = s.post(
                f"{httpbin_target[0]}/post",
                data=body_gen(),
                headers={"Content-Type": "application/octet-stream"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "Y2h1bmsxY2h1bmsyY2h1bmsz" in data.get("data", "")
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_iterable_body(selenium_jspi, httpbin_target):
    """Test POST with a generator/iterable body."""
    data = _inner_test_sync_iterable_body(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_iterable_body(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        def body_gen():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        async with AsyncSession() as s:
            response = await s.post(
                f"{httpbin_target[0]}/post",
                data=body_gen(),
                headers={"Content-Type": "application/octet-stream"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "Y2h1bmsxY2h1bmsyY2h1bmsz" in data.get("data", "")
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_iterable_body(selenium, httpbin_target):
    """Test async POST with a generator/iterable body."""
    data = _inner_test_async_iterable_body(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_iterable_str_body(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        def str_body_gen():
            yield "hello "
            yield "world"

        with Session() as s:
            response = s.post(
                f"{httpbin_target[0]}/post",
                data=str_body_gen(),
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data") == "hello world"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_iterable_str_body(selenium_jspi, httpbin_target):
    """Test POST with a generator yielding str chunks."""
    data = _inner_test_sync_iterable_str_body(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_iterable_str_body(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        def str_body_gen():
            yield "hello "
            yield "world"

        async with AsyncSession() as s:
            response = await s.post(
                f"{httpbin_target[0]}/post",
                data=str_body_gen(),
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data") == "hello world"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_iterable_str_body(selenium, httpbin_target):
    """Test async POST with a generator yielding str chunks."""
    data = _inner_test_async_iterable_str_body(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_async_iterable_body(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async def body_gen():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        async with AsyncSession() as s:
            response = await s.post(
                f"{httpbin_target[0]}/post",
                data=body_gen(),
                headers={"Content-Type": "application/octet-stream"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "Y2h1bmsxY2h1bmsyY2h1bmsz" in data.get("data", "")
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_async_iterable_body(selenium, httpbin_target):
    """Test async POST with an async generator body (covers __aiter__ path)."""
    data = _inner_test_async_async_iterable_body(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_async_iterable_str_body(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async def str_body_gen():
            yield "hello "
            yield "world"

        async with AsyncSession() as s:
            response = await s.post(
                f"{httpbin_target[0]}/post",
                data=str_body_gen(),
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("data") == "hello world"
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_async_iterable_str_body(selenium, httpbin_target):
    """Test async POST with an async generator yielding str chunks."""
    data = _inner_test_async_async_iterable_str_body(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_sse_raw_mode(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(f"{httpbin_target[2]}/sse?count=2&duration=1")
            assert response.status_code == 200

            ext = response.extension
            assert ext is not None

            events = []
            while True:
                event = ext.next_payload(raw=True)
                if event is None:
                    break
                assert isinstance(event, str)
                assert event.endswith("\n\n")
                events.append(event)

            assert len(events) >= 1
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_sse_raw_mode(selenium_jspi, httpbin_target):
    """Test sync SSE with raw=True returns raw event strings."""
    data = _inner_test_sync_sse_raw_mode(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_sse_raw_mode(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(f"{httpbin_target[2]}/sse?count=2&duration=1")
            assert response.status_code == 200

            ext = response.extension
            assert ext is not None

            events = []
            while True:
                event = await ext.next_payload(raw=True)
                if event is None:
                    break
                assert isinstance(event, str)
                assert event.endswith("\n\n")
                events.append(event)

            assert len(events) >= 1
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_sse_raw_mode(selenium, httpbin_target):
    """Test async SSE with raw=True returns raw event strings."""
    data = _inner_test_async_sse_raw_mode(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_sync_sse_via_stream(selenium_jspi, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import Session

        with Session() as s:
            response = s.get(
                f"{httpbin_target[0]}/sse?count=3&duration=1",
                stream=True,
            )
            assert response.status_code == 200

            chunks = []
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    chunks.append(chunk)

            assert len(chunks) >= 1
            raw = b"".join(chunks)
            # SSE events contain "data:" fields
            assert b"data:" in raw
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_sync_sse_via_stream(selenium_jspi, httpbin_target):
    """Test consuming an SSE endpoint as a plain stream (no sse:// scheme)."""
    data = _inner_test_sync_sse_via_stream(selenium_jspi, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_sse_via_stream(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get(
                f"{httpbin_target[0]}/sse?count=3&duration=1",
                stream=True,
            )
            assert response.status_code == 200

            chunks = []
            async for chunk in await response.iter_content(chunk_size=1024):
                if chunk:
                    chunks.append(chunk)

            assert len(chunks) >= 1
            raw = b"".join(chunks)
            # SSE events contain "data:" fields
            assert b"data:" in raw
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_sse_via_stream(selenium, httpbin_target):
    """Test consuming an SSE endpoint as a plain async stream (no sse:// scheme)."""
    data = _inner_test_async_sse_via_stream(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)


@run_in_pyodide(packages=["micropip"])
async def _inner_test_async_concurrent_gather(selenium, httpbin_target):
    import micropip

    await micropip.install(["./niquests-0.0.dev0-py3-none-any.whl", "coverage"], deps=True)

    import coverage

    cov = coverage.Coverage(source=["niquests"])
    cov.start()
    try:
        import asyncio

        from niquests import AsyncSession

        async with AsyncSession() as s:

            async def do_get(req_id):
                resp = await s.get(f"{httpbin_target[0]}/get?req={req_id}")
                return req_id, resp

            results = await asyncio.gather(
                do_get("a1"),
                do_get("b2"),
                do_get("c3"),
                do_get("d4"),
                do_get("e5"),
            )

            assert len(results) == 5

            seen_ids = set()
            for req_id, resp in results:
                assert resp.status_code == 200
                data = resp.json()
                assert data["args"]["req"] == [req_id]
                seen_ids.add(req_id)

            assert seen_ids == {"a1", "b2", "c3", "d4", "e5"}
    finally:
        cov.stop()
        cov.save()
    with open(".coverage", "rb") as f:
        return f.read()


def test_async_concurrent_gather(selenium, httpbin_target):
    """Test that 5 concurrent async requests via asyncio.gather all complete."""
    data = _inner_test_async_concurrent_gather(selenium, httpbin_target)
    if data:
        with open(f".coverage.pyodide.{uuid.uuid4().hex}", "wb") as f:
            f.write(data)
