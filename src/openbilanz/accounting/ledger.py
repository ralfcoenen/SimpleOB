"""Hauptbuch für den Buchhaltungskern von OpenBilanz-UG."""

from decimal import Decimal
from typing import Iterator

from openbilanz.accounting.account_balance import (
    ZERO,
    AccountBalance,
    to_decimal,
)
from openbilanz.accounting.ledger_entry import LedgerEntry
from openbilanz.domain.entry_side import EntrySide


class Ledger:
    """
    Verwaltet Konten und verarbeitet Soll-an-Haben-Buchungen.

    Ein Konto wird bei seiner ersten Verwendung automatisch angelegt.
    """

    def __init__(self) -> None:
        """Erzeugt ein leeres Hauptbuch."""
        self._accounts: dict[str, AccountBalance] = {}
        self._entries: list[LedgerEntry] = []

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
        debit_account_number = self._normalize_account_number(debit_account)
        credit_account_number = self._normalize_account_number(credit_account)
        decimal_amount = to_decimal(amount)

        if debit_account_number == credit_account_number:
            raise ValueError("Sollkonto und Habenkonto müssen verschieden sein.")

        if decimal_amount <= ZERO:
            raise ValueError("Ein Buchungsbetrag muss größer als 0,00 sein.")

        debit = self.get_or_create_account(debit_account_number)
        credit = self.get_or_create_account(credit_account_number)

        debit.add_debit(decimal_amount)
        credit.add_credit(decimal_amount)

    def get_or_create_account(self, account_number: str) -> AccountBalance:
        """
        Liefert ein vorhandenes Konto oder legt es neu an.

        Args:
            account_number:
                Kontonummer.

        Returns:
            Das zugehörige AccountBalance-Objekt.
        """
        normalized_account_number = self._normalize_account_number(account_number)

        if normalized_account_number not in self._accounts:
            self._accounts[normalized_account_number] = AccountBalance(
                account_number=normalized_account_number
            )

        return self._accounts[normalized_account_number]

    def get_account(self, account_number: str) -> AccountBalance:
        """
        Liefert ein vorhandenes Konto.

        Args:
            account_number:
                Kontonummer.

        Returns:
            Das zugehörige Konto.

        Raises:
            KeyError:
                Wenn das Konto nicht im Hauptbuch vorhanden ist.
        """
        normalized_account_number = self._normalize_account_number(account_number)

        try:
            return self._accounts[normalized_account_number]
        except KeyError as exc:
            raise KeyError(
                f"Das Konto {normalized_account_number!r} ist nicht vorhanden."
            ) from exc

    def has_account(self, account_number: str) -> bool:
        """
        Prüft, ob ein Konto vorhanden ist.

        Args:
            account_number:
                Kontonummer.
        """
        normalized_account_number = self._normalize_account_number(account_number)
        return normalized_account_number in self._accounts

    def add_entry(self, entry: LedgerEntry) -> None:
        """
        Speichert einen Hauptbucheintrag und aktualisiert den Kontostand.

        Raises:
            TypeError:
                Wenn kein LedgerEntry übergeben wird.
            ValueError:
                Wenn der Hauptbucheintrag bereits vorhanden ist.
        """
        if not isinstance(entry, LedgerEntry):
            raise TypeError("entry muss ein LedgerEntry sein.")

        if entry in self._entries:
            raise ValueError("Der Hauptbucheintrag ist bereits vorhanden.")

        account = self.get_or_create_account(entry.account_number)

        if entry.side is EntrySide.DEBIT:
            account.add_debit(entry.amount)
        else:
            account.add_credit(entry.amount)

        self._entries.append(entry)

    def entries(self) -> tuple[LedgerEntry, ...]:
        """
        Liefert alle Hauptbucheinträge in ihrer Einfügereihenfolge.

        Returns:
            Unveränderliche Folge der gespeicherten LedgerEntries.
        """
        return tuple(self._entries)

    def entries_for_account(
        self,
        account_number: str,
    ) -> tuple[LedgerEntry, ...]:
        """
        Liefert alle Hauptbucheinträge eines Kontos.

        Die Einträge bleiben in ihrer ursprünglichen Einfügereihenfolge.

        Args:
            account_number:
                Kontonummer des gesuchten Kontos.

        Returns:
            Unveränderliche Folge der passenden Hauptbucheinträge.
        """
        normalized_account_number = self._normalize_account_number(account_number)

        return tuple(
            entry
            for entry in self._entries
            if entry.account_number == normalized_account_number
        )

    def balances(self) -> tuple[AccountBalance, ...]:
        """
        Liefert alle Konten nach Kontonummer sortiert.

        Returns:
            Unveränderliche Folge der vorhandenen Konten.
        """
        return tuple(
            self._accounts[account_number]
            for account_number in sorted(self._accounts)
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
    def _normalize_account_number(account_number: str) -> str:
        """
        Prüft und normalisiert eine Kontonummer.

        Raises:
            TypeError:
                Wenn die Kontonummer keine Zeichenkette ist.
            ValueError:
                Wenn die Kontonummer leer ist.
        """
        if not isinstance(account_number, str):
            raise TypeError("Die Kontonummer muss eine Zeichenkette sein.")

        normalized_account_number = account_number.strip()

        if not normalized_account_number:
            raise ValueError("Die Kontonummer darf nicht leer sein.")

        return normalized_account_number
    