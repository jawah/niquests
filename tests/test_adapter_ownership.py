from __future__ import annotations

import asyncio
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from niquests.packages.urllib3 import AsyncHTTPResponse, HTTPResponse, ResponsePromise
from niquests.packages.urllib3.exceptions import MaxRetryError, NewConnectionError, ReadTimeoutError

import niquests.adapters as adapters
from niquests import Request
from niquests.adapters import AsyncHTTPAdapter, HTTPAdapter
from niquests.exceptions import ConnectionError, ReadTimeout


@pytest.fixture(params=[None, "http://proxy.test:8080", "proxy.test:8080"], ids=["direct", "proxy", "bare-proxy"])
def proxy_url(request):
    return request.param


def route(adapter, proxy_url):
    if proxy_url is None:
        return None, adapter.poolmanager
    return {"https": proxy_url}, adapter.proxy_manager_for("http://proxy.test:8080")


def prepared(host="first.test"):
    return Request("GET", "https://" + host + "/").prepare()


def low_response(asynchronous=False):
    response_type = AsyncHTTPResponse if asynchronous else HTTPResponse
    return response_type(body=b"ok", status=200, headers={"Content-Length": "2"})


def track_registration(monkeypatch, manager, result, fail=False):
    registered = []
    memorize = manager.pools.memorize

    def record(indicator, pool=None):
        if indicator is result:
            assert manager.pools.busy
            if fail:
                raise RuntimeError("registration failed")
            registered.append(pool)
        return memorize(indicator, pool)

    monkeypatch.setattr(manager.pools, "memorize", record)
    return registered


def change_proxy(request, *, proxies, **kwargs):
    proxies["https"] = "http://different-proxy.test:8081"


def failure(pool, url, kind):
    if kind == "timeout":
        raise ReadTimeoutError(pool, url, "timed out")
    raise MaxRetryError(pool, url, NewConnectionError(None, "connection refused"))


@pytest.mark.parametrize("kind, expected", [("timeout", ReadTimeout), ("refused", ConnectionError)])
def test_failed_send_releases_pool_and_allows_another_origin(monkeypatch, proxy_url, kind, expected):
    adapter = HTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    pools = []

    def urlopen(pool, method, url, **kwargs):
        assert manager.pools.busy
        pools.append(pool)
        if pool.host == "first.test":
            failure(pool, url, kind)
        return low_response()

    monkeypatch.setattr(adapters.HTTPSConnectionPool, "urlopen", urlopen)
    try:
        with pytest.raises(expected):
            adapter.send(prepared(), verify=False, proxies=proxies)
        # Check before another call from this thread can release a stale hold.
        assert not manager.pools.busy
        with ThreadPoolExecutor(max_workers=1) as executor:
            response = executor.submit(adapter.send, prepared("second.test"), verify=False, proxies=proxies).result(timeout=2)
        assert response.status_code == 200
        assert pools[0] is not pools[1]
        assert manager.pools.rsize() == 1
    finally:
        adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, expected", [("timeout", ReadTimeout), ("refused", ConnectionError)])
async def test_async_failed_send_releases_pool_and_allows_another_origin(monkeypatch, proxy_url, kind, expected):
    adapter = AsyncHTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    pools = []

    async def urlopen(pool, method, url, **kwargs):
        assert manager.pools.busy
        pools.append(pool)
        if pool.host == "first.test":
            failure(pool, url, kind)
        return low_response(asynchronous=True)

    monkeypatch.setattr(adapters.AsyncHTTPSConnectionPool, "urlopen", urlopen)
    try:
        with pytest.raises(expected):
            await adapter.send(prepared(), verify=False, proxies=proxies)
        assert not manager.pools.busy
        # A different task must acquire the next origin; same-task reuse masks the leak.
        response = await asyncio.wait_for(adapter.send(prepared("second.test"), verify=False, proxies=proxies), timeout=2)
        assert response.status_code == 200
        assert pools[0] is not pools[1]
        assert manager.pools.rsize() == 1
    finally:
        await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["timeout", "refused"])
async def test_failed_tasks_are_collectable_with_adapter_alive(monkeypatch, proxy_url, kind):
    adapter = AsyncHTTPAdapter(pool_connections=1)
    proxies, _ = route(adapter, proxy_url)

    async def urlopen(pool, method, url, **kwargs):
        failure(pool, url, kind)

    async def attempt():
        try:
            await adapter.send(prepared(), verify=False, proxies=proxies)
        except ConnectionError:
            pass
        except ReadTimeout:
            pass

    monkeypatch.setattr(adapters.AsyncHTTPSConnectionPool, "urlopen", urlopen)
    try:
        references = []
        for _ in range(4):
            task = asyncio.create_task(attempt())
            references.append(weakref.ref(task))
            await task
            del task
        # Let the event loop discard its references to completed task callbacks.
        await asyncio.sleep(0)
        gc.collect()
        assert all(reference() is None for reference in references)
    finally:
        await adapter.close()


SETUP_FAILURES = ["certificate", "request_url", "headers", "timeout", "body", "extension", "saturation"]


def setup_failure(monkeypatch, adapter, request, kind, tmp_path, asynchronous):
    kwargs = {"verify": False}

    def fail(*args, **kwargs):
        raise ValueError("setup failed")

    if kind == "certificate":
        kwargs["verify"] = str(tmp_path / "missing-ca.pem")
        return kwargs, OSError
    if kind == "request_url":
        monkeypatch.setattr(adapter, "request_url", fail)
    elif kind == "headers":
        monkeypatch.setattr(adapter, "add_headers", fail)
    elif kind == "timeout":
        kwargs["timeout"] = (1, 2, 3, 4)
    elif kind == "body":
        request.body = {}
    elif kind == "extension":

        def change_scheme(request, **kwargs):
            request.url = "unknown-extension://first.test/"

        monkeypatch.setattr(adapter, "add_headers", change_scheme)
        monkeypatch.setattr(adapters, "async_load_extension" if asynchronous else "load_extension", fail)
    elif kind == "saturation":
        pool_type = adapters.AsyncHTTPSConnectionPool if asynchronous else adapters.HTTPSConnectionPool
        monkeypatch.setattr(pool_type, "is_saturated", property(lambda self: True))
        monkeypatch.setattr(pool_type, "is_idle", property(lambda self: False))
        if asynchronous:

            async def async_fail(*args, **kwargs):
                fail()

            monkeypatch.setattr(pool_type, "get_response", async_fail)
        else:
            monkeypatch.setattr(pool_type, "get_response", fail)
        kwargs["multiplexed"] = True
    return kwargs, ValueError


@pytest.mark.parametrize("kind", SETUP_FAILURES)
def test_setup_failure_releases_pool(monkeypatch, tmp_path, proxy_url, kind):
    adapter = HTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    request = prepared()
    kwargs, error = setup_failure(monkeypatch, adapter, request, kind, tmp_path, False)
    try:
        with pytest.raises(error):
            adapter.send(request, proxies=proxies, **kwargs)
        assert not manager.pools.busy
    finally:
        adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", SETUP_FAILURES)
async def test_async_setup_failure_releases_pool(monkeypatch, tmp_path, proxy_url, kind):
    adapter = AsyncHTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    request = prepared()
    kwargs, error = setup_failure(monkeypatch, adapter, request, kind, tmp_path, True)
    try:
        with pytest.raises(error):
            await adapter.send(request, proxies=proxies, **kwargs)
        assert not manager.pools.busy
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_cancellation_releases_pool(monkeypatch, proxy_url):
    adapter = AsyncHTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)

    async def urlopen(pool, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(adapters.AsyncHTTPSConnectionPool, "urlopen", urlopen)
    try:
        with pytest.raises(asyncio.CancelledError):
            await adapter.send(prepared(), verify=False, proxies=proxies)
        assert not manager.pools.busy
    finally:
        await adapter.close()


@pytest.mark.parametrize("mutate_proxy", [False, True])
@pytest.mark.parametrize("promise", [False, True], ids=["response", "promise"])
def test_success_keeps_registration_and_releases_pool(monkeypatch, proxy_url, promise, mutate_proxy):
    adapter = HTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    owner = []
    result = ResponsePromise(SimpleNamespace(_http_vsn_str="HTTP/2"), 1, []) if promise else low_response()
    registered = track_registration(monkeypatch, manager, result)
    if mutate_proxy:
        proxies = proxies or {}
        monkeypatch.setattr(adapter, "add_headers", change_proxy)

    def urlopen(pool, **kwargs):
        owner.append(pool)
        return result

    monkeypatch.setattr(adapters.HTTPSConnectionPool, "urlopen", urlopen)
    try:
        response = adapter.send(prepared(), verify=False, proxies=proxies, multiplexed=promise)
        assert not manager.pools.busy
        assert registered == owner
        assert manager.pools.locate(result, block=False) is owner[0]
        manager.pools.release()
        if promise:
            assert response._promise is result
            assert result.get_parameter("niquests_response") is response
        else:
            assert response.raw is result
    finally:
        adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutate_proxy", [False, True])
@pytest.mark.parametrize("promise", [False, True], ids=["response", "promise"])
async def test_async_success_keeps_registration_and_releases_pool(monkeypatch, proxy_url, promise, mutate_proxy):
    adapter = AsyncHTTPAdapter(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    owner = []
    result = ResponsePromise(SimpleNamespace(_http_vsn_str="HTTP/2"), 1, []) if promise else low_response(asynchronous=True)
    registered = track_registration(monkeypatch, manager, result)
    if mutate_proxy:
        proxies = proxies or {}
        monkeypatch.setattr(adapter, "add_headers", change_proxy)

    async def urlopen(pool, **kwargs):
        owner.append(pool)
        return result

    monkeypatch.setattr(adapters.AsyncHTTPSConnectionPool, "urlopen", urlopen)
    try:
        response = await adapter.send(prepared(), verify=False, proxies=proxies, multiplexed=promise)
        assert not manager.pools.busy
        assert registered == owner
        assert await manager.pools.locate(result, block=False) is owner[0]
        manager.pools.release()
        if promise:
            assert response._promise is result
            assert result.get_parameter("niquests_response") is response
        else:
            assert response.raw is result
    finally:
        await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("stage", ["callback", "registration"])
async def test_untranslated_failure_releases_pool(monkeypatch, proxy_url, asynchronous, stage):
    adapter = (AsyncHTTPAdapter if asynchronous else HTTPAdapter)(pool_connections=1)
    proxies, manager = route(adapter, proxy_url)
    result = low_response(asynchronous)
    if stage == "registration":
        track_registration(monkeypatch, manager, result, fail=True)

    def callback(_):
        if stage == "callback":
            raise RuntimeError("callback failed")

    async def async_callback(info):
        callback(info)

    def urlopen(pool, **kwargs):
        kwargs["on_post_connection"](None)
        return result

    async def async_urlopen(pool, **kwargs):
        await kwargs["on_post_connection"](None)
        return result

    monkeypatch.setattr(adapters.HTTPSConnectionPool, "urlopen", urlopen)
    monkeypatch.setattr(adapters.AsyncHTTPSConnectionPool, "urlopen", async_urlopen)
    try:
        with pytest.raises(RuntimeError, match=stage + " failed"):
            if asynchronous:
                await adapter.send(prepared(), verify=False, proxies=proxies, on_post_connection=async_callback)
            else:
                adapter.send(prepared(), verify=False, proxies=proxies, on_post_connection=callback)
        assert not manager.pools.busy
    finally:
        if asynchronous:
            await adapter.close()
        else:
            adapter.close()
