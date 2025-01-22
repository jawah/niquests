from __future__ import annotations

import typing

try:
    from urllib3 import __version__

    HAS_LEGACY_URLLIB3: bool = int(__version__.split(".")[-1]) < 900
except (ValueError, ImportError):  # Defensive: tested in separate CI
    # Means one of the two cases:
    #   1) urllib3 does not exist -> fallback to urllib3_future
    #   2) urllib3 exist but not fork -> fallback to urllib3_future
    HAS_LEGACY_URLLIB3 = True

if HAS_LEGACY_URLLIB3:  # Defensive: tested in separate CI
    import urllib3_future
else:
    urllib3_future = None  # type: ignore[assignment]

try:
    import urllib3

    # force detect broken or dummy urllib3 package
    urllib3.Timeout  # noqa
    urllib3.Retry  # noqa
    urllib3.__version__  # noqa
except (ImportError, AttributeError):  # Defensive: tested in separate CI
    urllib3 = None  # type: ignore[assignment]


if (urllib3 is None and urllib3_future is None) or (HAS_LEGACY_URLLIB3 and urllib3_future is None):
    raise RuntimeError(  # Defensive: tested in separate CI
        "This is awkward but your environment is missing urllib3-future. "
        "Your environment seems broken. "
        "You may fix this issue by running `python -m pip install niquests -U` "
        "to force reinstall its dependencies."
    )

if urllib3 is not None:
    T = typing.TypeVar("T", urllib3.Timeout, urllib3.Retry)
else:  # Defensive: tested in separate CI
    T = typing.TypeVar("T", urllib3_future.Timeout, urllib3_future.Retry)  # type: ignore


def urllib3_ensure_type(o: T) -> T:
    """Retry, Timeout must be the one in urllib3_future."""
    if urllib3 is None:
        return o

    if HAS_LEGACY_URLLIB3:  # Defensive: tested in separate CI
        if "urllib3_future" not in str(type(o)):
            assert urllib3_future is not None

            if isinstance(o, urllib3.Timeout):
                return urllib3_future.Timeout(  # type: ignore[return-value]
                    o.total,  # type: ignore[arg-type]
                    o.connect_timeout,  # type: ignore[arg-type]
                    o.read_timeout,  # type: ignore[arg-type]
                )
            if isinstance(o, urllib3.Retry):
                return urllib3_future.Retry(  # type: ignore[return-value]
                    o.total,
                    o.connect,
                    o.read,
                    redirect=o.redirect,
                    status=o.status,
                    other=o.other,
                    allowed_methods=o.allowed_methods,
                    status_forcelist=o.status_forcelist,
                    backoff_factor=o.backoff_factor,
                    backoff_max=o.backoff_max,
                    raise_on_redirect=o.raise_on_redirect,
                    raise_on_status=o.raise_on_status,
                    history=o.history,  # type: ignore[arg-type]
                    respect_retry_after_header=o.respect_retry_after_header,
                    remove_headers_on_redirect=o.remove_headers_on_redirect,
                    backoff_jitter=o.backoff_jitter,
                )

    return o
