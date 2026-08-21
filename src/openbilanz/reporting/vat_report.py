"""Read Model für die Umsatzsteuer-Auswertung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openbilanz.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class VatReport:
    """Umsatzsteuer-Auswertung für einen Berichtszeitraum."""

    start_date: date
    end_date: date
    output_tax_7: Decimal
    output_tax_19: Decimal
    input_tax_7: Decimal
    input_tax_19: Decimal

    @property
    def output_tax_total(self) -> Decimal:
        """Gesamte Umsatzsteuer."""

        return self.output_tax_7 + self.output_tax_19

    @property
    def input_tax_total(self) -> Decimal:
        """Gesamte Vorsteuer."""

        return self.input_tax_7 + self.input_tax_19

    @property
    def vat_payable(self) -> Decimal:
        """Umsatzsteuer-Zahllast; negativ bei Vorsteuerüberschuss."""

        return self.output_tax_total - self.input_tax_total

    @property
    def input_tax_surplus(self) -> Decimal:
        """Vorsteuerüberschuss, andernfalls 0,00."""

        return max(-self.vat_payable, ZERO)
