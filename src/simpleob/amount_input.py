"""Gemeinsame Verarbeitung deutscher Betragseingaben."""

from decimal import Decimal, InvalidOperation


def parse_german_amount(
    value: str,
) -> Decimal:
    """Liest einen Geldbetrag in deutscher Schreibweise."""

    normalized = (
        value.strip()
        .replace(".", "")
        .replace(",", ".")
    )

    if not normalized:
        raise ValueError(
            "Der Betrag darf nicht leer sein."
        )

    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(
            "Ungültiger Geldbetrag."
        ) from exc


def format_german_amount(
    value: Decimal,
) -> str:
    """Formatiert einen Geldbetrag mit zwei Nachkommastellen."""

    formatted = f"{value:,.2f}"

    return (
        formatted
        .replace(",", "\0")
        .replace(".", ",")
        .replace("\0", ".")
    )


def normalize_german_amount(
    value: str,
) -> str:
    """Normalisiert eine gültige Betragseingabe."""

    return format_german_amount(
        parse_german_amount(value)
    )
