"""Normalisierung deutscher Steuernummern."""

import re


class TaxNumberNormalizer:
    """Wandelt landesspezifische Steuernummern in das 13-stellige Bundesschema um."""

    def normalize(
        self,
        *,
        federal_state: str,
        tax_number: str,
    ) -> str:
        """Normalisiert eine Steuernummer für das angegebene Bundesland."""

        if not isinstance(federal_state, str):
            raise TypeError(
                "federal_state muss eine Zeichenkette sein."
            )

        if not isinstance(tax_number, str):
            raise TypeError(
                "tax_number muss eine Zeichenkette sein."
            )

        if federal_state == "NW":
            return self._normalize_north_rhine_westphalia(
                tax_number
            )

        raise ValueError(
            "Bundesland wird noch nicht unterstützt."
        )

    @staticmethod
    def _normalize_north_rhine_westphalia(
        tax_number: str,
    ) -> str:
        """Normalisiert eine nordrhein-westfälische Steuernummer."""

        normalized = re.sub(
            r"[\s/]",
            "",
            tax_number,
        )

        if (
            len(normalized) != 11
            or not normalized.isdigit()
        ):
            raise ValueError(
                "Ungültige Steuernummer für Nordrhein-Westfalen."
            )

        finanzamt = normalized[:3]
        bezirk = normalized[3:7]
        unterscheidung = normalized[7:]

        return (
            "5"
            + finanzamt
            + "0"
            + bezirk
            + unterscheidung
        )

