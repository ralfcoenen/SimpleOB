"""Umsatzsteuerkonten einer Buchhaltung."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VatAccounts:
    """Konfiguriert die Umsatzsteuerkonten eines Mandanten."""

    input_tax_7: str
    input_tax_19: str
    output_tax_7: str
    output_tax_19: str

    def __post_init__(self) -> None:
        for field_name, account_number in (
            ("input_tax_7", self.input_tax_7),
            ("input_tax_19", self.input_tax_19),
            ("output_tax_7", self.output_tax_7),
            ("output_tax_19", self.output_tax_19),
        ):
            if not isinstance(account_number, str):
                raise TypeError(
                    f"{field_name} must be a str"
                )

            if not account_number.strip():
                raise ValueError(
                    f"{field_name} must not be blank"
                )

            if account_number != account_number.strip():
                raise ValueError(
                    f"{field_name} must not contain "
                    "surrounding whitespace"
                )

            if not account_number.isdigit():
                raise ValueError(
                    f"{field_name} must contain digits only"
                )

    @property
    def account_numbers(self) -> frozenset[str]:
        """Liefert alle konfigurierten Umsatzsteuerkonten."""

        return frozenset(
            (
                self.input_tax_7,
                self.input_tax_19,
                self.output_tax_7,
                self.output_tax_19,
            )
        )
