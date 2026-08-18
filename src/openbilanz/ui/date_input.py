"""Gemeinsame Verarbeitung deutscher Datumseingaben."""

from datetime import date, datetime


def parse_german_date(
    value: str,
) -> date:
    """Liest ein deutsches Datum aus mehreren Eingabeformaten."""

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "Das Datum darf nicht leer sein."
        )

    if normalized.isdigit():
        if len(normalized) == 8:
            formats = (
                "%d%m%Y",
            )
        elif len(normalized) == 6:
            formats = (
                "%d%m%y",
            )
        else:
            formats = ()
    else:
        formats = (
            "%d.%m.%Y",
            "%d.%m.%y",
        )

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                normalized,
                date_format,
            ).date()
        except ValueError:
            continue

        if date_format.endswith("%y"):
            parsed = parsed.replace(
                year=2000 + parsed.year % 100
            )

        return parsed

    raise ValueError(
        "Ungültiges Datum. "
        "Erlaubt sind z. B. "
        "18.08.2026, 18.08.26, "
        "18082026 oder 180826."
    )

def format_german_date(
    value: date,
) -> str:
    """Formatiert ein Datum als TT.MM.JJJJ."""

    return value.strftime(
        "%d.%m.%Y"
    )


def normalize_german_date(
    value: str,
) -> str:
    """Normalisiert eine gültige Datumseingabe auf TT.MM.JJJJ."""

    return format_german_date(
        parse_german_date(value)
    )