"""
requests.structures
~~~~~~~~~~~~~~~~~~~

Data structures that power Requests.
"""

from __future__ import annotations

import threading
import typing
from collections.abc import Mapping, MutableMapping

try:
    from ._compat import HAS_LEGACY_URLLIB3

    if not HAS_LEGACY_URLLIB3:
        from urllib3._collections import _lower_wrapper  # type: ignore[attr-defined]
    else:  # Defensive: tested in separate/isolated CI
        from urllib3_future._collections import (
            _lower_wrapper,  # type: ignore[attr-defined]
        )
except ImportError:
    from functools import lru_cache

    @lru_cache(maxsize=64)
    def _lower_wrapper(string: str) -> str:
        """backport"""
        return string.lower()


from .exceptions import InvalidHeader


def _ensure_str_or_bytes(key: typing.Any, value: typing.Any) -> tuple[bytes | str, bytes | str]:
    if isinstance(key, (bytes, str)) and isinstance(value, (bytes, str)):
        return key, value
    if isinstance(
        value,
        (
            float,
            int,
        ),
    ):
        value = str(value)
    if isinstance(key, (bytes, str)) is False or (value is not None and isinstance(value, (bytes, str)) is False):
        raise InvalidHeader(f"Illegal header name or value {key}")
    return key, value


class CaseInsensitiveDict(MutableMapping):
    """A case-insensitive ``dict``-like object.

    Implements all methods and operations of
    ``MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.

    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    def __init__(self, data=None, **kwargs) -> None:
        self._store: MutableMapping[bytes | str, tuple[bytes | str, ...]] = {}
        if data is None:
            data = {}

        # given object is most likely to be urllib3.HTTPHeaderDict or follow a similar implementation that we can trust
        if hasattr(data, "getlist"):
            self._store = data._container.copy()
        elif isinstance(data, CaseInsensitiveDict):
            self._store = data._store.copy()  # type: ignore[attr-defined]
        else:  # otherwise, we must ensure given iterable contains type we can rely on
            if data or kwargs:
                if hasattr(data, "items"):
                    self.update(data, **kwargs)
                else:
                    self.update(
                        {k: v for k, v in data},
                        **kwargs,
                    )

    def __setitem__(self, key: str | bytes, value: str | bytes) -> None:
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[_lower_wrapper(key)] = _ensure_str_or_bytes(key, value)

    def __getitem__(self, key) -> bytes | str:
        e = self._store[_lower_wrapper(key)]
        if len(e) == 2:
            return e[1]
        # this path should always be list[str] (if coming from urllib3.HTTPHeaderDict!)
        try:
            return ", ".join(e[1:]) if isinstance(e[1], str) else b", ".join(e[1:])  # type: ignore[arg-type]
        except TypeError:  # worst case scenario...
            return ", ".join(v.decode() if isinstance(v, bytes) else v for v in e[1:])

    def __delitem__(self, key) -> None:
        del self._store[_lower_wrapper(key)]

    def __iter__(self) -> typing.Iterator[str | bytes]:
        for key_ci in self._store:
            yield self._store[key_ci][0]

    def __len__(self) -> int:
        return len(self._store)

    def lower_items(self) -> typing.Iterator[tuple[bytes | str, bytes | str]]:
        """Like iteritems(), but with all lowercase keys."""
        return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())

    def items(self):
        for k in self._store:
            t = self._store[k]
            if len(t) == 2:
                yield t
            else:  # this case happen due to copying "_container" from HTTPHeaderDict!
                try:
                    yield t[0], ", ".join(t[1:])  # type: ignore[arg-type]
                except TypeError:
                    yield (
                        t[0],
                        ", ".join(v.decode() if isinstance(v, bytes) else v for v in t[1:]),
                    )

    def __eq__(self, other) -> bool:
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self) -> CaseInsensitiveDict:
        return CaseInsensitiveDict(self)

    def __repr__(self) -> str:
        return str(dict(self.items()))

    def __contains__(self, item: str) -> bool:  # type: ignore[override]
        return _lower_wrapper(item) in self._store


class LookupDict(dict):
    """Dictionary lookup object."""

    def __init__(self, name=None) -> None:
        self.name: str | None = name
        super().__init__()

    def __repr__(self):
        return f"<lookup '{self.name}'>"

    def __getitem__(self, key):
        # We allow fall-through here, so values default to None
        return self.__dict__.get(key, None)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)


class SharableLimitedDict(typing.MutableMapping):
    def __init__(self, max_size: int | None) -> None:
        self._store: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._max_size = max_size
        self._lock: threading.RLock | DummyLock = threading.RLock()

    def __getstate__(self) -> dict[str, typing.Any]:
        return {"_store": self._store, "_max_size": self._max_size}

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        self._lock = threading.RLock()
        self._store = state["_store"]
        self._max_size = state["_max_size"]

    def __delitem__(self, __key) -> None:
        with self._lock:
            del self._store[__key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __iter__(self) -> typing.Iterator:
        with self._lock:
            return iter(self._store)

    def __setitem__(self, key, value):
        with self._lock:
            if self._max_size and len(self._store) >= self._max_size:
                self._store.popitem()

            self._store[key] = value

    def __getitem__(self, item):
        with self._lock:
            return self._store[item]


class QuicSharedCache(SharableLimitedDict):
    def __init__(self, max_size: int | None) -> None:
        super().__init__(max_size)
        self._exclusion_store: typing.MutableMapping[typing.Any, typing.Any] = {}

    def add_domain(self, host: str, port: int | None = None, alt_port: int | None = None) -> None:
        if port is None:
            port = 443
        if alt_port is None:
            alt_port = port
        self[(host, port)] = (host, alt_port)

    def exclude_domain(self, host: str, port: int | None = None, alt_port: int | None = None):
        if port is None:
            port = 443
        if alt_port is None:
            alt_port = port
        self._exclusion_store[(host, port)] = (host, alt_port)

    def __setitem__(self, key, value):
        with self._lock:
            if key in self._exclusion_store:
                return

            if self._max_size and len(self._store) >= self._max_size:
                self._store.popitem()

            self._store[key] = value


class AsyncQuicSharedCache(QuicSharedCache):
    def __init__(self, max_size: int | None) -> None:
        super().__init__(max_size)
        self._lock = DummyLock()

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        self._lock = DummyLock()
        self._store = state["_store"]
        self._max_size = state["_max_size"]


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def acquire(self):
        pass

    def release(self):
        pass
