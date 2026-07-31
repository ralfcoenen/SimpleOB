"""Hilfsfunktionen für Geldbeträge der Domäne."""

from decimal import Decimal, InvalidOperation
from typing import Final

ZERO: Final[Decimal] = Decimal("0.00")


def to_decimal(value: Decimal | str | int) -> Decimal:
    """
    Wandelt einen unterstützten Wert in Decimal um.

    Float-Werte werden absichtlich nicht akzeptiert.
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

