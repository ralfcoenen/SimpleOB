"""Status eines Anlageguts."""

from enum import Enum


class FixedAssetStatus(Enum):
    """Lebenszyklusstatus eines Anlageguts."""

    ACTIVE = "ACTIVE"
    DISPOSED = "DISPOSED"
    