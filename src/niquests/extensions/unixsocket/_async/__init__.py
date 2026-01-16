from __future__ import annotations

import socket
import typing
from urllib.parse import unquote

from ...._constant import DEFAULT_POOLBLOCK
from ....adapters import AsyncHTTPAdapter
from ....exceptions import RequestException
from ....packages.urllib3._async.connection import AsyncHTTPConnection
from ....packages.urllib3._async.connectionpool import AsyncHTTPConnectionPool
from ....packages.urllib3._async.poolmanager import AsyncPoolManager
from ....packages.urllib3.contrib.ssa import AsyncSocket
from ....typing import CacheLayerAltSvcType
from ....utils import select_proxy


class AsyncUnixHTTPConnection(AsyncHTTPConnection):
    def __init__(self, host, **kwargs):
        super().__init__(host, **kwargs)
        self.host: str = unquote(self.host)
        self.socket_path = self.host
        self.host = self.socket_path.split("/")[-1]

    async def connect(self):
        sock = AsyncSocket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        await sock.connect(self.socket_path)
        self.sock = sock
        await self._post_conn()


class AsyncUnixHTTPConnectionPool(AsyncHTTPConnectionPool):
    ConnectionCls = AsyncUnixHTTPConnection


class AsyncUnixAdapter(AsyncHTTPAdapter):
    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        quic_cache_layer: CacheLayerAltSvcType | None = None,
        **pool_kwargs: typing.Any,
    ):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self._quic_cache_layer = quic_cache_layer

        self.poolmanager = AsyncPoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            preemptive_quic_cache=quic_cache_layer,
            **pool_kwargs,
        )
        self.poolmanager.key_fn_by_scheme["http+unix"] = self.poolmanager.key_fn_by_scheme["http"]
        self.poolmanager.pool_classes_by_scheme = {
            "http+unix": AsyncUnixHTTPConnectionPool,
        }

    def get_connection(self, url, proxies=None):
        proxy = select_proxy(url, proxies)

        if proxy:
            raise RequestException("unix socket cannot be associated with proxies")

        return self.poolmanager.connection_from_url(url)

    def request_url(self, request, proxies):
        return request.path_url


__all__ = ("AsyncUnixAdapter",)
