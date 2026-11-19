"""Rollen eines mandantenspezifischen Personenkontos."""

from enum import Enum


class PersonAccountRole(str, Enum):
    DEBITOR = "DEBITOR"
    KREDITOR = "KREDITOR"

    @property
    def number_range(self) -> tuple[int, int]:
        if self is PersonAccountRole.DEBITOR:
            return 10000, 69999
        return 70000, 99999
