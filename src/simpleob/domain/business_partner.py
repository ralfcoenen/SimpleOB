"""Mandantenbezogener Geschäftspartner für die OP-Verwaltung."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class BusinessPartner:
    """Ein Kunde, Lieferant oder beides innerhalb eines Mandanten."""

    company_id: UUID
    name: str
    is_customer: bool = True
    is_supplier: bool = False
    is_active: bool = True
    partner_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if not isinstance(self.partner_id, UUID):
            raise TypeError("partner_id must be a UUID")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Der Name des Geschäftspartners darf nicht leer sein.")
        if not isinstance(self.is_customer, bool):
            raise TypeError("is_customer must be a bool")
        if not isinstance(self.is_supplier, bool):
            raise TypeError("is_supplier must be a bool")
        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be a bool")
        if not self.is_customer and not self.is_supplier:
            raise ValueError(
                "Ein Geschäftspartner muss Kunde, Lieferant oder beides sein."
            )
        object.__setattr__(self, "name", self.name.strip())
