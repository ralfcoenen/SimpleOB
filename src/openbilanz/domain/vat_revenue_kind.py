"""Arten von Ausgangsumsätzen für die Umsatzsteuer."""


from enum import Enum


class VatRevenueKind(str, Enum):
    """Fachliche Art eines Ausgangsumsatzes."""

    NORMAL = "NORMAL"
    FIXED_ASSET_DISPOSAL = "FIXED_ASSET_DISPOSAL"
