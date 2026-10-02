"""Abgeleitete Werte des Betriebsvermögensvergleichs."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BvvEvaluation:
    """Aus der Buchführung abgeleiteter Betriebsvermögensvergleich."""

    current_hgb_equity: Decimal
    previous_hgb_equity: Decimal

    current_depreciation_difference: Decimal
    previous_depreciation_difference: Decimal

    current_book_value_difference: Decimal
    previous_book_value_difference: Decimal

    current_tax_equity: Decimal
    previous_tax_equity: Decimal

    contribution: Decimal
    withdrawal_distribution: Decimal

    profit_loss: Decimal

    @property
    def change_in_tax_equity(self) -> Decimal:
        """Liefert die Veränderung des steuerlichen Betriebsvermögens."""

        return self.current_tax_equity - self.previous_tax_equity
