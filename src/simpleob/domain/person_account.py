"""Mandantenbezogene Verknüpfung eines Kontos mit einem Geschäftspartner."""

from dataclasses import dataclass
from uuid import UUID

from simpleob.domain.account import Account
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.person_account_role import PersonAccountRole


@dataclass(frozen=True, slots=True)
class PersonAccount:
    account: Account
    partner: BusinessPartner
    role: PersonAccountRole

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("account must be an Account")
        if not isinstance(self.partner, BusinessPartner):
            raise TypeError("partner must be a BusinessPartner")
        if not isinstance(self.role, PersonAccountRole):
            raise TypeError("role must be a PersonAccountRole")
        if self.account.account_type.name != (
            "ASSET" if self.role is PersonAccountRole.DEBITOR else "LIABILITY"
        ):
            raise ValueError("Personenkonto-Rolle und Kontotyp stimmen nicht überein.")
        if self.role is PersonAccountRole.DEBITOR and not self.partner.is_customer:
            raise ValueError("Ein Debitor muss als Kunde geführt werden.")
        if self.role is PersonAccountRole.KREDITOR and not self.partner.is_supplier:
            raise ValueError("Ein Kreditor muss als Lieferant geführt werden.")

    @property
    def company_id(self) -> UUID:
        return self.partner.company_id

    @property
    def account_number(self) -> str:
        return self.account.number
