"""Soll- und Habenseiten für Buchungszeilen."""

from enum import Enum


class EntrySide(str, Enum):
    """
    Kennzeichnet die Seite einer Buchungszeile.

    DEBIT entspricht der Sollseite.
    CREDIT entspricht der Habenseite.
    """

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

    @property
    def german_name(self) -> str:
        """Liefert die deutsche Bezeichnung der Buchungsseite."""
        if self is EntrySide.DEBIT:
            return "Soll"

        return "Haben"

    @classmethod
    def from_value(cls, value: "EntrySide | str") -> "EntrySide":
        """
        Wandelt eine Buchungsseiten-Angabe in EntrySide um.

        Akzeptierte Zeichenketten:

        - DEBIT
        - CREDIT
        - SOLL
        - HABEN

        Groß- und Kleinschreibung sowie umgebende Leerzeichen
        werden ignoriert.

        Args:
            value:
                EntrySide-Objekt oder Zeichenkette.

        Returns:
            Die entsprechende Buchungsseite.

        Raises:
            TypeError:
                Wenn der Wert weder EntrySide noch str ist.
            ValueError:
                Wenn die Zeichenkette keine gültige Seite bezeichnet.
        """
        if isinstance(value, cls):
            return value

        if not isinstance(value, str):
            raise TypeError(
                "Die Buchungsseite muss als EntrySide oder str "
                "übergeben werden."
            )

        normalized_value = value.strip().upper()

        aliases = {
            "DEBIT": cls.DEBIT,
            "SOLL": cls.DEBIT,
            "CREDIT": cls.CREDIT,
            "HABEN": cls.CREDIT,
        }

        try:
            return aliases[normalized_value]
        except KeyError as exc:
            raise ValueError(
                f"{value!r} ist keine gültige Buchungsseite."
            ) from exc

    def __str__(self) -> str:
        """Liefert den technischen Wert der Buchungsseite."""
        return self.value
    