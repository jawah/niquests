from ._typing import TimeoutType

#: Default timeout (total) assigned for GET, HEAD, and OPTIONS methods.
READ_DEFAULT_TIMEOUT: TimeoutType = 30
#: Default timeout (total) assigned for DELETE, PUT, PATCH, and POST.
WRITE_DEFAULT_TIMEOUT: TimeoutType = 120

DEFAULT_POOLBLOCK: bool = False
DEFAULT_POOLSIZE: int = 10
DEFAULT_RETRIES: int = 0
