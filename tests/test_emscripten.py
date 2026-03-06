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
