"""Kontensalden für den Buchhaltungskern von OpenBilanz-UG."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Final


ZERO: Final[Decimal] = Decimal("0.00")


def to_decimal(value: Decimal | str | int) -> Decimal:
    """
    Wandelt einen unterstützten Wert in Decimal um.

    Float-Werte werden absichtlich nicht akzeptiert, weil sie bereits
    Rundungsabweichungen enthalten können.

    Args:
        value:
            Geldbetrag als Decimal, Zeichenkette oder ganze Zahl.

    Returns:
        Der Wert als Decimal mit zwei Nachkommastellen.

    Raises:
        TypeError:
            Wenn der Wert einen nicht unterstützten Datentyp besitzt.
        ValueError:
            Wenn der Wert nicht als Dezimalzahl interpretiert werden kann.
    """
    if isinstance(value, bool):
        raise TypeError("Boolesche Werte sind keine gültigen Geldbeträge.")

    if isinstance(value, float):
        raise TypeError(
            "Float-Werte sind für Geldbeträge nicht zulässig. "
            'Verwende beispielsweise Decimal("10.50") oder "10.50".'
        )

    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, (str, int)):
        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(
                f"Der Wert {value!r} ist kein gültiger Geldbetrag."
            ) from exc
    else:
        raise TypeError(
            "Geldbeträge müssen als Decimal, str oder int übergeben werden."
        )

    if not decimal_value.is_finite():
        raise ValueError("Geldbeträge müssen endliche Zahlen sein.")

    return decimal_value.quantize(Decimal("0.01"))


@dataclass(slots=True)
class AccountBalance:
    """
    Enthält die Soll- und Habenumsätze eines Kontos.

    Der rechnerische Saldo wird als Soll minus Haben dargestellt:

        positiver Saldo = Sollsaldo
        negativer Saldo = Habensaldo
    """

    account_no: str
    debit: Decimal = field(default_factory=lambda: ZERO)
    credit: Decimal = field(default_factory=lambda: ZERO)

    def __post_init__(self) -> None:
        """Validiert und normalisiert die Anfangswerte."""
        self.account_no = self.account_no.strip()

        if not self.account_no:
            raise ValueError("Die Kontonummer darf nicht leer sein.")

        self.debit = to_decimal(self.debit)
        self.credit = to_decimal(self.credit)

        if self.debit < ZERO:
            raise ValueError("Der Sollumsatz darf nicht negativ sein.")

        if self.credit < ZERO:
            raise ValueError("Der Habenumsatz darf nicht negativ sein.")

    @property
    def balance(self) -> Decimal:
        """
        Liefert den rechnerischen Kontosaldo.

        Returns:
            Sollumsatz minus Habenumsatz.
        """
        return self.debit - self.credit

    @property
    def debit_balance(self) -> Decimal:
        """
        Liefert den Sollsaldo.

        Bei einem Habensaldo wird 0,00 zurückgegeben.
        """
        return max(self.balance, ZERO)

    @property
    def credit_balance(self) -> Decimal:
        """
        Liefert den Habensaldo als positiven Betrag.

        Bei einem Sollsaldo wird 0,00 zurückgegeben.
        """
        return max(-self.balance, ZERO)

    def add_debit(self, amount: Decimal | str | int) -> None:
        """
        Addiert einen Betrag zum Sollumsatz.

        Args:
            amount:
                Positiver Geldbetrag.
        """
        decimal_amount = self._validate_posting_amount(amount)
        self.debit += decimal_amount

    def add_credit(self, amount: Decimal | str | int) -> None:
        """
        Addiert einen Betrag zum Habenumsatz.

        Args:
            amount:
                Positiver Geldbetrag.
        """
        decimal_amount = self._validate_posting_amount(amount)
        self.credit += decimal_amount

    @staticmethod
    def _validate_posting_amount(
        amount: Decimal | str | int,
    ) -> Decimal:
        """Validiert einen zu buchenden Betrag."""
        decimal_amount = to_decimal(amount)

        if decimal_amount <= ZERO:
            raise ValueError("Ein Buchungsbetrag muss größer als 0,00 sein.")

        return decimal_amount
    