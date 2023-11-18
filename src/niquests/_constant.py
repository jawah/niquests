from __future__ import annotations

import wassima

from ._typing import RetryType, TimeoutType

#: Default timeout (total) assigned for GET, HEAD, and OPTIONS methods.
READ_DEFAULT_TIMEOUT: TimeoutType = 30
#: Default timeout (total) assigned for DELETE, PUT, PATCH, and POST.
WRITE_DEFAULT_TIMEOUT: TimeoutType = 120

DEFAULT_POOLBLOCK: bool = False
DEFAULT_POOLSIZE: int = 10
DEFAULT_RETRIES: RetryType = 0

#: Kept for BC
DEFAULT_CA_BUNDLE: str = wassima.generate_ca_bundle()
