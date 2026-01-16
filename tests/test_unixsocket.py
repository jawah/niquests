from __future__ import annotations

import sys

import pytest

from niquests import AsyncSession, Session


@pytest.mark.skipif(sys.platform != "linux", reason="Unix sockets only available on Linux")
class TestUnixSocketSync:
    """Synchronous Unix socket tests."""

    def test_docker_version_info(self):
        """Fetch Docker version info via Unix socket."""

        with Session() as session:
            response = session.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/version")

            assert response.status_code == 200
            data = response.json()
            assert "Version" in data
            assert "ApiVersion" in data

    def test_docker_404_unknown_path(self):
        """Request unknown Docker API path returns 404."""

        with Session() as session:
            response = session.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/nonexistent/path")

            assert response.status_code == 404


@pytest.mark.skipif(sys.platform != "linux", reason="Unix sockets only available on Linux")
class TestUnixSocketAsync:
    """Asynchronous Unix socket tests."""

    @pytest.mark.asyncio
    async def test_docker_version_info(self):
        """Fetch Docker version info via Unix socket asynchronously."""

        async with AsyncSession() as session:
            response = await session.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/version")

            assert response.status_code == 200
            data = response.json()
            assert "Version" in data
            assert "ApiVersion" in data

    @pytest.mark.asyncio
    async def test_docker_404_unknown_path(self):
        """Request unknown Docker API path returns 404 asynchronously."""

        async with AsyncSession() as session:
            response = await session.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/nonexistent/path")

            assert response.status_code == 404
