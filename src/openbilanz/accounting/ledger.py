"""Hauptbuch für den Buchhaltungskern von OpenBilanz-UG."""

from decimal import Decimal
from typing import Iterator

from openbilanz.accounting.account_balance import (
    AccountBalance,
    ZERO,
    to_decimal,
)


class Ledger:
    """
    Verwaltet Konten und verarbeitet Soll-an-Haben-Buchungen.

    Ein Konto wird bei seiner ersten Verwendung automatisch angelegt.
    """

    def __init__(self) -> None:
        """Erzeugt ein leeres Hauptbuch."""
        self._accounts: dict[str, AccountBalance] = {}

    def post(
        self,
        debit_account: str,
        credit_account: str,
        amount: Decimal | str | int,
    ) -> None:
        """
        Verbucht einen Betrag im Soll und im Haben.

        Args:
            debit_account:
                Kontonummer des Sollkontos.
            credit_account:
                Kontonummer des Habenkontos.
            amount:
                Positiver Buchungsbetrag.

        Raises:
            ValueError:
                Wenn eine Kontonummer leer ist, beide Konten identisch
                sind oder der Betrag nicht größer als 0,00 ist.
            TypeError:
                Wenn ein nicht unterstützter Betragstyp verwendet wird.
        """
        debit_account_no = self._normalize_account_no(debit_account)
        credit_account_no = self._normalize_account_no(credit_account)
        decimal_amount = to_decimal(amount)

        if debit_account_no == credit_account_no:
            raise ValueError(
                "Sollkonto und Habenkonto müssen verschieden sein."
            )

        if decimal_amount <= ZERO:
            raise ValueError("Ein Buchungsbetrag muss größer als 0,00 sein.")

        debit = self.get_or_create_account(debit_account_no)
        credit = self.get_or_create_account(credit_account_no)

        debit.add_debit(decimal_amount)
        credit.add_credit(decimal_amount)

    def get_or_create_account(self, account_no: str) -> AccountBalance:
        """
        Liefert ein vorhandenes Konto oder legt es neu an.

        Args:
            account_no:
                Kontonummer.

        Returns:
            Das zugehörige AccountBalance-Objekt.
        """
        normalized_account_no = self._normalize_account_no(account_no)

        if normalized_account_no not in self._accounts:
            self._accounts[normalized_account_no] = AccountBalance(
                account_no=normalized_account_no
            )

        return self._accounts[normalized_account_no]

    def get_account(self, account_no: str) -> AccountBalance:
        """
        Liefert ein vorhandenes Konto.

        Args:
            account_no:
                Kontonummer.

        Returns:
            Das zugehörige Konto.

        Raises:
            KeyError:
                Wenn das Konto nicht im Hauptbuch vorhanden ist.
        """
        normalized_account_no = self._normalize_account_no(account_no)

        try:
            return self._accounts[normalized_account_no]
        except KeyError as exc:
            raise KeyError(
                f"Das Konto {normalized_account_no!r} ist nicht vorhanden."
            ) from exc

    def has_account(self, account_no: str) -> bool:
        """
        Prüft, ob ein Konto vorhanden ist.

        Args:
            account_no:
                Kontonummer.
        """
        normalized_account_no = self._normalize_account_no(account_no)
        return normalized_account_no in self._accounts

    def balances(self) -> tuple[AccountBalance, ...]:
        """
        Liefert alle Konten nach Kontonummer sortiert.

        Returns:
            Unveränderliche Folge der vorhandenen Konten.
        """
        return tuple(
            self._accounts[account_no]
            for account_no in sorted(self._accounts)
        )

    @property
    def debit_total(self) -> Decimal:
        """Liefert die Summe aller Sollumsätze."""
        return sum(
            (account.debit for account in self._accounts.values()),
            start=ZERO,
        )

    @property
    def credit_total(self) -> Decimal:
        """Liefert die Summe aller Habenumsätze."""
        return sum(
            (account.credit for account in self._accounts.values()),
            start=ZERO,
        )

    @property
    def is_balanced(self) -> bool:
        """Prüft, ob Soll- und Habenumsätze übereinstimmen."""
        return self.debit_total == self.credit_total

    def __len__(self) -> int:
        """Liefert die Anzahl der Konten."""
        return len(self._accounts)

    def __iter__(self) -> Iterator[AccountBalance]:
        """Ermöglicht die sortierte Iteration über alle Konten."""
        return iter(self.balances())

    @staticmethod
    def _normalize_account_no(account_no: str) -> str:
        """
        Prüft und normalisiert eine Kontonummer.

        Raises:
            TypeError:
                Wenn die Kontonummer keine Zeichenkette ist.
            ValueError:
                Wenn die Kontonummer leer ist.
        """
        if not isinstance(account_no, str):
            raise TypeError("Die Kontonummer muss eine Zeichenkette sein.")

        normalized_account_no = account_no.strip()

        if not normalized_account_no:
            raise ValueError("Die Kontonummer darf nicht leer sein.")

        return normalized_account_no