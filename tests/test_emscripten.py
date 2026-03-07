from __future__ import annotations

import pytest

# Handle the import safely. If pytest-pyodide is not installed (e.g. checks in IDE),
# we define a dummy decorator to avoid NameError/ImportError during local editing/collection.
try:
    from pytest_pyodide import run_in_pyodide
except ImportError:

    def run_in_pyodide(*args, **kwargs):
        def decorator(func):
            return pytest.mark.skip(reason="pytest-pyodide not installed")(func)

        return decorator


@run_in_pyodide(packages=["micropip"])
async def test_sync_basic_get(selenium_jspi):
    """Test basic GET request works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session

    with Session() as s:
        response = s.get("https://httpbingo.org/get")
        assert response.status_code == 200
        assert "headers" in response.json()


@run_in_pyodide(packages=["micropip"])
async def test_sync_basic_post(selenium_jspi):
    """Test basic POST request works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session

    with Session() as s:
        response = s.post("https://httpbingo.org/post", json={"test": "data"})
        assert response.status_code == 200
        data = response.json()
        assert data["json"] == {"test": "data"}


@run_in_pyodide(packages=["micropip"])
async def test_sync_streaming_read(selenium_jspi):
    """Test streaming response works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session

    with Session() as s:
        response = s.get("https://httpbingo.org/stream/5", stream=True)
        assert response.status_code == 200

        chunks = []
        for chunk in response.iter_lines():
            if chunk:
                chunks.append(chunk)

        assert len(chunks) == 5


@run_in_pyodide(packages=["micropip"])
async def test_sync_retry_works(selenium_jspi):
    """Test that retry mechanism works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session

    with Session(retries=3) as s:
        response = s.get("https://httpbingo.org/get")
        assert response.status_code == 200


@run_in_pyodide(packages=["micropip"])
async def test_async_basic_get(selenium):
    """Test basic async GET request works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get("https://httpbingo.org/get")
        assert response.status_code == 200
        assert "headers" in response.json()


@run_in_pyodide(packages=["micropip"])
async def test_async_basic_post(selenium):
    """Test basic async POST request works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.post("https://httpbingo.org/post", json={"test": "data"})
        assert response.status_code == 200
        data = response.json()
        assert data["json"] == {"test": "data"}


@run_in_pyodide(packages=["micropip"])
async def test_async_streaming_read(selenium):
    """Test async streaming response works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get("https://httpbingo.org/stream/5", stream=True)
        assert response.status_code == 200

        chunks = []
        async for chunk in response.iter_lines():
            if chunk:
                chunks.append(chunk)

        assert len(chunks) == 5


@run_in_pyodide(packages=["micropip"])
async def test_async_retry_works(selenium):
    """Test that async retry mechanism works."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import AsyncSession

    async with AsyncSession(retries=3) as s:
        response = await s.get("https://httpbingo.org/get")
        assert response.status_code == 200


@run_in_pyodide(packages=["micropip"])
async def test_sync_websocket(selenium_jspi):
    """Test sync WebSocket via browser native API + JSPI."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    import sys

    if "emscripten" not in sys.platform:
        return  # skip outside Pyodide

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    from niquests import Session

    with Session() as s:
        response = s.get("wss://echo.websocket.org")
        assert response.status_code == 101

        ext = response.extension
        assert ext is not None
        assert ext.closed is False

        # Consume potential welcome/greeting message from the server
        welcome = ext.next_payload()
        assert isinstance(welcome, str)

        ext.send_payload("hello from niquests")
        msg = ext.next_payload()
        assert isinstance(msg, str)
        assert msg == "hello from niquests"

        ext.close()
        assert ext.closed is True


@run_in_pyodide(packages=["micropip"])
async def test_sync_websocket_binary(selenium_jspi):
    """Test sync WebSocket binary message handling."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    from niquests import Session

    with Session() as s:
        response = s.get("wss://echo.websocket.org")
        assert response.status_code == 101

        ext = response.extension

        # Consume potential welcome/greeting message from the server
        ext.next_payload()

        ext.send_payload(b"\x00\x01\x02\x03")
        msg = ext.next_payload()
        assert isinstance(msg, bytes)
        assert msg == b"\x00\x01\x02\x03"

        ext.close()


@run_in_pyodide(packages=["micropip"])
async def test_async_websocket(selenium):
    """Test async WebSocket via browser native API."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get("wss://echo.websocket.org")
        assert response.status_code == 101

        ext = response.extension
        assert ext is not None
        assert ext.closed is False

        # Consume potential welcome/greeting message from the server
        welcome = await ext.next_payload()
        assert isinstance(welcome, str)

        await ext.send_payload("hello from niquests async")
        msg = await ext.next_payload()
        assert isinstance(msg, str)
        assert msg == "hello from niquests async"

        await ext.close()
        assert ext.closed is True


@run_in_pyodide(packages=["micropip"])
async def test_async_websocket_binary(selenium):
    """Test async WebSocket binary message handling."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get("wss://echo.websocket.org")
        assert response.status_code == 101

        ext = response.extension

        # Consume potential welcome/greeting message from the server
        await ext.next_payload()

        await ext.send_payload(b"\x00\x01\x02\x03")
        msg = await ext.next_payload()
        assert isinstance(msg, bytes)
        assert msg == b"\x00\x01\x02\x03"

        await ext.close()


@run_in_pyodide(packages=["micropip"])
async def test_sync_sse(selenium_jspi):
    """Test sync SSE via pyfetch streaming + manual parsing."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session
    from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent

    with Session() as s:
        response = s.get("sse://httpbingo.org/sse?count=3&duration=1")
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


@run_in_pyodide(packages=["micropip"])
async def test_async_sse(selenium):
    """Test async SSE via pyfetch streaming + manual parsing."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import AsyncSession
    from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent

    async with AsyncSession() as s:
        response = await s.get("sse://httpbingo.org/sse?count=3&duration=1")
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


@run_in_pyodide(packages=["micropip"])
async def test_sync_sse_send_raises(selenium_jspi):
    """Test that SSE send_payload raises NotImplementedError."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    from niquests import Session

    with Session() as s:
        response = s.get("sse://httpbingo.org/sse?count=1&duration=1")
        ext = response.extension

        raised = False
        try:
            ext.send_payload("test")
        except NotImplementedError:
            raised = True

        assert raised is True
        ext.close()


@run_in_pyodide(packages=["micropip"])
async def test_sync_websocket_close_from_server(selenium_jspi):
    """Test that close works and state is updated."""
    try:
        import niquests  # noqa: F401
    except ImportError:
        import micropip

        await micropip.install("./niquests-0.0.dev0-py3-none-any.whl", deps=True)

    try:
        from js import WebSocket  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("websocket support unavailable on platform")

    from niquests import Session

    with Session() as s:
        response = s.get("wss://echo.websocket.org")
        ext = response.extension
        assert ext.closed is False

        # Close from our side, then verify state
        ext.close()
        assert ext.closed is True
