from __future__ import annotations

import socket
import typing
from urllib.parse import unquote

from ..._constant import DEFAULT_POOLBLOCK
from ...adapters import HTTPAdapter
from ...exceptions import RequestException
from ...packages.urllib3.connection import HTTPConnection
from ...packages.urllib3.connectionpool import HTTPConnectionPool
from ...packages.urllib3.poolmanager import PoolManager
from ...typing import CacheLayerAltSvcType
from ...utils import select_proxy


class UnixHTTPConnection(HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host: str = unquote(self.host)
        self.socket_path = self.host
        self.host = self.socket_path.split("/")[-1]

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock
        self._post_conn()


class UnixHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = UnixHTTPConnection


class UnixAdapter(HTTPAdapter):
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

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            preemptive_quic_cache=quic_cache_layer,
            **pool_kwargs,
        )
        self.poolmanager.key_fn_by_scheme["http+unix"] = self.poolmanager.key_fn_by_scheme["http"]
        self.poolmanager.pool_classes_by_scheme = {
            "http+unix": UnixHTTPConnectionPool,
        }

    def get_connection(self, url, proxies=None):
        proxy = select_proxy(url, proxies)

        if proxy:
            raise RequestException("unix socket cannot be associated with proxies")

        return self.poolmanager.connection_from_url(url)

    def request_url(self, request, proxies):
        return request.path_url

    def close(self):
        self.poolmanager.clear()


__all__ = ("UnixAdapter",)
