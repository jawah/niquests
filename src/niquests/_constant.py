from __future__ import annotations

from .typing import RetryType, TimeoutType

#: Default timeout (total) assigned for GET, HEAD, and OPTIONS methods.
READ_DEFAULT_TIMEOUT: TimeoutType = 30
#: Default timeout (total) assigned for DELETE, PUT, PATCH, and POST.
WRITE_DEFAULT_TIMEOUT: TimeoutType = 120

DEFAULT_POOLBLOCK: bool = False
DEFAULT_POOLSIZE: int = 10
DEFAULT_RETRIES: RetryType = 0


# we don't want to eagerly load this as some user just
# don't leverage ssl anyway. this should make niquests
# import generally faster.
def __getattr__(name: str):
    if name == "DEFAULT_CA_BUNDLE":
        import wassima

        val = wassima.generate_ca_bundle()
        globals()["DEFAULT_CA_BUNDLE"] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
