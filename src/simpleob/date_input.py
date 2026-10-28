"""Gemeinsame Verarbeitung deutscher Datumseingaben."""

from datetime import date, datetime

from PySide6.QtWidgets import QLineEdit


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


class GermanDateEdit(QLineEdit):
    """Textbasiertes Datumseingabefeld ohne Kalenderauswahl.

    Das Feld verwendet dieselbe Parsing- und Formatierungslogik wie die
    bestehenden Datumshilfen. Ungültige Eingaben werden bei
    :meth:`date_value` abgewiesen; gültige Werte werden dabei stets als
    ``TT.MM.JJJJ`` zurückgeschrieben. Bei optionalen Feldern liefert ein
    leerer Inhalt ``None``.
    """

    def __init__(
        self,
        parent=None,
        *,
        value: date | None = None,
        optional: bool = False,
    ) -> None:
        super().__init__(parent)
        self._optional = optional
        if value is not None:
            self.set_date(value)
        self.editingFinished.connect(self.normalize)

    def date_value(self) -> date | None:
        """Liefert das Datum und normalisiert das Feld bei Erfolg."""

        value = self.text().strip()
        if not value and self._optional:
            return None

        parsed = parse_german_date(value)
        self.setText(format_german_date(parsed))
        return parsed

    def set_date(self, value: date | None) -> None:
        """Setzt ein Datum im einheitlichen Anzeigeformat."""

        if value is None:
            if not self._optional:
                raise ValueError(
                    "Ein Pflicht-Datumsfeld benötigt einen Datumswert."
                )
            self.clear()
            return

        if not isinstance(value, date):
            raise TypeError("Der Wert muss ein datetime.date sein.")
        self.setText(format_german_date(value))

    def normalize(self) -> None:
        """Normalisiert eine gültige Eingabe nach dem Verlassen des Felds."""

        if not self.text().strip() and self._optional:
            self.clear()
            return

        try:
            self.setText(normalize_german_date(self.text()))
        except ValueError:
            # Die Eingabe bleibt sichtbar; date_value() weist sie beim
            # Übernehmen mit derselben zentralen Fehlermeldung zurück.
            return
