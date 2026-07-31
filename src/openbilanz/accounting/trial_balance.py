"""Summen- und Saldenliste für OpenBilanz-UG."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator

from openbilanz.domain.money import ZERO
from openbilanz.accounting.ledger import Ledger


@dataclass(frozen=True, slots=True)
class TrialBalanceRow:
    """
    Eine Zeile der Summen- und Saldenliste.

    Die Salden werden getrennt als Sollsaldo und Habensaldo dargestellt.
    Dadurch enthält jede Zeile höchstens auf einer Saldo-Seite einen Betrag.
    """

    account_no: str
    debit_turnover: Decimal
    credit_turnover: Decimal
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalance:
    """
    Erzeugt eine Summen- und Saldenliste aus einem Hauptbuch.
    """

    def __init__(self, ledger: Ledger) -> None:
        """
        Initialisiert die Summen- und Saldenliste.

        Args:
            ledger:
                Das auszuwertende Hauptbuch.

        Raises:
            TypeError:
                Wenn kein Ledger übergeben wird.
        """
        if not isinstance(ledger, Ledger):
            raise TypeError("ledger muss eine Instanz von Ledger sein.")

        self._ledger = ledger

    @property
    def ledger(self) -> Ledger:
        """Liefert das zugrunde liegende Hauptbuch."""
        return self._ledger

    def rows(self) -> tuple[TrialBalanceRow, ...]:
        """
        Liefert alle Konten als sortierte Auswertungszeilen.

        Returns:
            Unveränderliche Folge von TrialBalanceRow-Objekten.
        """
        return tuple(
            TrialBalanceRow(
                account_no=account.account_no,
                debit_turnover=account.debit,
                credit_turnover=account.credit,
                debit_balance=account.debit_balance,
                credit_balance=account.credit_balance,
            )
            for account in self._ledger
        )

    @property
    def debit_turnover_total(self) -> Decimal:
        """Liefert die Summe aller Sollumsätze."""
        return sum(
            (row.debit_turnover for row in self.rows()),
            start=ZERO,
        )

    @property
    def credit_turnover_total(self) -> Decimal:
        """Liefert die Summe aller Habenumsätze."""
        return sum(
            (row.credit_turnover for row in self.rows()),
            start=ZERO,
        )

    @property
    def debit_balance_total(self) -> Decimal:
        """Liefert die Summe aller Sollsalden."""
        return sum(
            (row.debit_balance for row in self.rows()),
            start=ZERO,
        )

    @property
    def credit_balance_total(self) -> Decimal:
        """Liefert die Summe aller Habensalden."""
        return sum(
            (row.credit_balance for row in self.rows()),
            start=ZERO,
        )

    @property
    def is_turnover_balanced(self) -> bool:
        """Prüft, ob Soll- und Habenumsätze übereinstimmen."""
        return self.debit_turnover_total == self.credit_turnover_total

    @property
    def is_balance_balanced(self) -> bool:
        """Prüft, ob Soll- und Habensalden übereinstimmen."""
        return self.debit_balance_total == self.credit_balance_total

    def __len__(self) -> int:
        """Liefert die Anzahl der Auswertungszeilen."""
        return len(self._ledger)

    def __iter__(self) -> Iterator[TrialBalanceRow]:
        """Ermöglicht die Iteration über die Auswertungszeilen."""
        return iter(self.rows())
