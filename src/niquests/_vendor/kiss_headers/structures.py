from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, MutableMapping
from typing import (
    Any,
    Iterator,
    List,
    Optional,
    Tuple,
)
from typing import (
    MutableMapping as MutableMappingType,
)

from .utils import normalize_str

"""
Disclaimer : CaseInsensitiveDict has been borrowed from `psf/requests`.
Minors changes has been made.
"""


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

    def __init__(self, data: Mapping | None = None, **kwargs: Any):
        self._store: OrderedDict = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key: str, value: Any) -> None:
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[normalize_str(key)] = (key, value)

    def __getitem__(self, key: str) -> Any:
        return self._store[normalize_str(key)][1]

    def __delitem__(self, key: str) -> None:
        del self._store[normalize_str(key)]

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def lower_items(self) -> Iterator[tuple[str, Any]]:
        """Like iteritems(), but with all lowercase keys."""
        return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self) -> CaseInsensitiveDict:
        return CaseInsensitiveDict(dict(self._store.values()))

    def __repr__(self) -> str:
        return str(dict(self.items()))


AttributeDescription = Tuple[List[Optional[str]], List[int]]
AttributeBag = MutableMappingType[str, AttributeDescription]
