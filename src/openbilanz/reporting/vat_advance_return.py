"""Read Model für die Umsatzsteuer-Voranmeldung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openbilanz.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class VatAdvanceReturn:
    """USt-VA-Auswertung für einen Berichtszeitraum."""

    start_date: date
    end_date: date

    taxable_turnover_7: Decimal
    taxable_turnover_19: Decimal

    output_tax_7: Decimal
    output_tax_19: Decimal

    input_tax_7: Decimal
    input_tax_19: Decimal

    @property
    def taxable_turnover_total(self) -> Decimal:
        """Gesamte steuerpflichtige Bemessungsgrundlage."""

        return (
            self.taxable_turnover_7
            + self.taxable_turnover_19
        )

    @property
    def output_tax_total(self) -> Decimal:
        """Gesamte Umsatzsteuer."""

        return (
            self.output_tax_7
            + self.output_tax_19
        )

    @property
    def input_tax_total(self) -> Decimal:
        """Gesamte Vorsteuer."""

        return (
            self.input_tax_7
            + self.input_tax_19
        )

    @property
    def vat_payable(self) -> Decimal:
        """USt-Zahllast; negativ bei Vorsteuerüberschuss."""

        return (
            self.output_tax_total
            - self.input_tax_total
        )

    @property
    def input_tax_surplus(self) -> Decimal:
        """Vorsteuerüberschuss, andernfalls 0,00."""

        return max(
            -self.vat_payable,
            ZERO,
        )
