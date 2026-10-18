"""Summen- und Saldenbericht."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from simpleob.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class TrialBalanceReportRow:
    """Eine Zeile der Summen- und Saldenliste."""

    account_number: str
    opening_debit: Decimal
    opening_credit: Decimal
    debit_turnover: Decimal
    credit_turnover: Decimal
    closing_debit: Decimal
    closing_credit: Decimal


@dataclass(frozen=True, slots=True)
class TrialBalanceReport:
    """Summen- und Saldenliste für einen Berichtszeitraum."""

    start_date: date
    end_date: date
    rows: tuple[TrialBalanceReportRow, ...]

    @property
    def opening_debit_total(self) -> Decimal:
        """Summe der Soll-Anfangssalden."""

        return sum(
            (row.opening_debit for row in self.rows),
            start=ZERO,
        )

    @property
    def opening_credit_total(self) -> Decimal:
        """Summe der Haben-Anfangssalden."""

        return sum(
            (row.opening_credit for row in self.rows),
            start=ZERO,
        )

    @property
    def debit_turnover_total(self) -> Decimal:
        """Summe der Sollumsätze."""

        return sum(
            (row.debit_turnover for row in self.rows),
            start=ZERO,
        )

    @property
    def credit_turnover_total(self) -> Decimal:
        """Summe der Habenumsätze."""

        return sum(
            (row.credit_turnover for row in self.rows),
            start=ZERO,
        )

    @property
    def closing_debit_total(self) -> Decimal:
        """Summe der Soll-Endsalden."""

        return sum(
            (row.closing_debit for row in self.rows),
            start=ZERO,
        )

    @property
    def closing_credit_total(self) -> Decimal:
        """Summe der Haben-Endsalden."""

        return sum(
            (row.closing_credit for row in self.rows),
            start=ZERO,
        )
