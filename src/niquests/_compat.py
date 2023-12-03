from __future__ import annotations

try:
    from urllib3._version import __version__

    HAS_LEGACY_URLLIB3: bool = int(__version__.split(".")[-1]) < 900
except (ValueError, ImportError):
    # Means one of the two cases:
    #   1) urllib3 does not exist -> fallback to urllib3_future
    #   2) urllib3 exist but not fork -> fallback to urllib3_future
    HAS_LEGACY_URLLIB3 = True
