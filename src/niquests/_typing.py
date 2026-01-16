from __future__ import annotations

import warnings

warnings.warn(
    (
        "importing niquests._typing is deprecated and absolutely discouraged. "
        "It will be removed in a future release. In general, never import private "
        "modules."
    ),
    DeprecationWarning,
)

from .typing import *  # noqa
