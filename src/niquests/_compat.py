from __future__ import annotations

try:
    from urllib3._version import __version__

    HAS_LEGACY_URLLIB3: bool = int(__version__.split(".")[-1]) < 900
except (ValueError, ImportError):
    HAS_LEGACY_URLLIB3 = True
