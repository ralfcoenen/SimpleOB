from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, eq=False)
class Company:
    """Ein fachlich identifiziertes Unternehmen."""

    company_id: UUID
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(self.name, str):
            raise TypeError("name must be a str")

        if not self.name.strip():
            raise ValueError("name must not be blank")

        if self.name != self.name.strip():
            raise ValueError("name must not contain surrounding whitespace")
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Company):
            return NotImplemented

        return self.company_id == other.company_id

    def __hash__(self) -> int:
        return hash(self.company_id)