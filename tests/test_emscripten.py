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


# We explicitly point to the local wheel file (created by nox) instead of PyPI
@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
def test_sync_basic_get(selenium):
    """Test basic GET request works."""
    from niquests import Session

    with Session() as s:
        response = s.get("https://httpbin.org/get")
        assert response.status_code == 200
        assert "headers" in response.json()


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
def test_sync_basic_post(selenium):
    """Test basic POST request works."""
    from niquests import Session

    with Session() as s:
        response = s.post(
            "https://httpbin.org/post",
            json={"test": "data"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["json"] == {"test": "data"}


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
def test_sync_streaming_read(selenium):
    """Test streaming response works."""
    from niquests import Session

    with Session() as s:
        response = s.get(
            "https://httpbin.org/stream/5",
            stream=True
        )
        assert response.status_code == 200

        chunks = []
        for chunk in response.iter_lines():
            if chunk:
                chunks.append(chunk)

        assert len(chunks) == 5


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
def test_sync_retry_works(selenium):
    """Test that retry mechanism works."""
    from niquests import Session

    with Session(retries=3) as s:
        response = s.get("https://httpbin.org/get")
        assert response.status_code == 200


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
async def test_async_basic_get(selenium):
    """Test basic async GET request works."""
    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get("https://httpbin.org/get")
        assert response.status_code == 200
        assert "headers" in response.json()


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
async def test_async_basic_post(selenium):
    """Test basic async POST request works."""
    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.post(
            "https://httpbin.org/post",
            json={"test": "data"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["json"] == {"test": "data"}


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
async def test_async_streaming_read(selenium):
    """Test async streaming response works."""
    from niquests import AsyncSession

    async with AsyncSession() as s:
        response = await s.get(
            "https://httpbin.org/stream/5",
            stream=True
        )
        assert response.status_code == 200

        chunks = []
        async for chunk in await response.iter_lines():
            if chunk:
                chunks.append(chunk)

        assert len(chunks) == 5


@run_in_pyodide(packages=["/home/ahmed/PycharmProjects/niquests/dist/niquests-3.17.0-py3-none-any.whl"])
async def test_async_retry_works(selenium):
    """Test that async retry mechanism works."""
    from niquests import AsyncSession

    async with AsyncSession(retries=3) as s:
        response = await s.get("https://httpbin.org/get")
        assert response.status_code == 200
