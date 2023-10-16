"""
requests.structures
~~~~~~~~~~~~~~~~~~~

Data structures that power Requests.
"""

from __future__ import annotations

import threading
import typing
from collections import OrderedDict
from collections.abc import Mapping, MutableMapping


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
        self._store: MutableMapping[
            bytes | str, tuple[bytes | str, bytes | str]
        ] = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key: str | bytes, value: str | bytes) -> None:
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key) -> bytes | str:
        return self._store[key.lower()][1]

    def __delitem__(self, key) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> typing.Iterator[str | bytes]:
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def lower_items(self) -> typing.Iterator[tuple[bytes | str, bytes | str]]:
        """Like iteritems(), but with all lowercase keys."""
        return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())

    def __eq__(self, other) -> bool:
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self) -> CaseInsensitiveDict:
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self) -> str:
        return str(dict(self.items()))


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
    def __init__(self, max_size: int) -> None:
        self._store: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._max_size = max_size
        self._lock = threading.Lock()

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
            if len(self._store) >= self._max_size:
                self._store.popitem()

            self._store[key] = value

    def __getitem__(self, item):
        with self._lock:
            return self._store[item]


class QuicSharedCache(SharableLimitedDict):
    def add_domain(
        self, host: str, port: int | None = None, alt_port: int | None = None
    ) -> None:
        if port is None:
            port = 443
        if alt_port is None:
            alt_port = port
        self[(host, port)] = (host, alt_port)
