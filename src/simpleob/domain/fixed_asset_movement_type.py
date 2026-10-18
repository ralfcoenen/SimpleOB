"""Art einer Anlagenbewegung."""

from enum import Enum


class FixedAssetMovementType(Enum):
    """Fachliche Art einer Anlagenbewegung."""

    ACQUISITION = "ACQUISITION"
    DISPOSAL = "DISPOSAL"
    LOSS = "LOSS"
    REVERSAL = "REVERSAL"
