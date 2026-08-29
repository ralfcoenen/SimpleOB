"""Arten der Vereinnahmung von Ausgangsumsätzen."""


from enum import Enum


class VatPaymentKind(str, Enum):
    """Zeitpunkt der Vereinnahmung eines Ausgangsumsatzes."""

    IMMEDIATE = "IMMEDIATE"
    RECEIVABLE = "RECEIVABLE"
