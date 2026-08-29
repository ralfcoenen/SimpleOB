"""Status der Kleinunternehmerprüfung."""

from enum import Enum


class SmallBusinessVatStatus(Enum):
    """Ergebnis der Prüfung nach § 19 UStG."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
