from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RevocationStrategy(Enum):
    PREFER_OCSP = 0
    PREFER_CRL = 1
    CHECK_ALL = 2


@dataclass
class RevocationConfiguration:
    strategy: RevocationStrategy | None = RevocationStrategy.PREFER_OCSP
    strict_mode: bool = False


DEFAULT_STRATEGY: RevocationConfiguration = RevocationConfiguration()
