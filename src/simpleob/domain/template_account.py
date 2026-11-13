from dataclasses import dataclass

from simpleob.domain.account_type import AccountType


def validate_ebilanz_account_description(value: str) -> None:
    """Prüft die für ERiC nachweislich unzulässige Kontenbezeichnung.

    Die verfügbare ERiC-Regel meldet U+2013 (EN DASH) für
    ``accountDescription`` als ungültig. Eine vollständige Zeichensatzliste
    liegt SimpleOB nicht vor; deshalb werden keine weiteren Zeichen verworfen.
    """

    if not isinstance(value, str):
        raise TypeError("account description must be a string")

    if "\u2013" in value:
        raise ValueError(
            "Die Kontenbezeichnung enthält U+2013 (EN DASH), das ERiC im "
            "E-Bilanz-Kontennachweis zurückweist. Bitte geben Sie an dieser "
            "Stelle einen ASCII-Bindestrich (-) ein."
        )


@dataclass(frozen=True, slots=True)
class TemplateAccount:
    account_number: str
    name: str
    account_type: AccountType

    def __post_init__(self) -> None:
        if not isinstance(self.account_number, str):
            raise TypeError("account_number must be a string")

        if not self.account_number.strip():
            raise ValueError("account_number must not be blank")

        if self.account_number != self.account_number.strip():
            raise ValueError("account_number must not have surrounding whitespace")

        if not self.account_number.isdigit():
            raise ValueError("account_number must contain digits only")

        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

        if not self.name.strip():
            raise ValueError("name must not be blank")

        if self.name != self.name.strip():
            raise ValueError("name must not have surrounding whitespace")

        if not isinstance(self.account_type, AccountType):
            raise TypeError("account_type must be an AccountType")
