"""Normalisierung deutscher Steuernummern."""

import re


class TaxNumberNormalizer:
    """Wandelt Landes-Steuernummern in das 13-stellige ELSTER-Schema um."""

    _TWO_DIGIT_OFFICE_PREFIXES = {
        "BW": "28",
        "BE": "11",
        "HB": "24",
        "HH": "22",
        "HE": "26",
        "NI": "23",
        "RP": "27",
        "SH": "21",
    }

    _THREE_DIGIT_OFFICE_PREFIXES = {
        "BY": "9",
        "BB": "3",
        "MV": "4",
        "SL": "1",
        "SN": "3",
        "ST": "3",
        "TH": "4",
    }

    def normalize(
        self,
        *,
        federal_state: str,
        tax_number: str,
    ) -> str:
        """Normalisiert eine Steuernummer für das angegebene Bundesland."""

        if not isinstance(
            federal_state,
            str,
        ):
            raise TypeError(
                "federal_state muss eine Zeichenkette sein."
            )

        if not isinstance(
            tax_number,
            str,
        ):
            raise TypeError(
                "tax_number muss eine Zeichenkette sein."
            )

        normalized = self._digits(tax_number)

        if federal_state == "NW":
            return self._normalize_north_rhine_westphalia(
                normalized
            )

        if federal_state == "HE":
            return self._normalize_hesse(
                normalized
            )

        if federal_state in self._TWO_DIGIT_OFFICE_PREFIXES:
            return self._normalize_two_digit_office_state(
                federal_state=federal_state,
                tax_number=normalized,
            )

        if federal_state in self._THREE_DIGIT_OFFICE_PREFIXES:
            return self._normalize_three_digit_office_state(
                federal_state=federal_state,
                tax_number=normalized,
            )

        raise ValueError(
            "Bundesland wird nicht unterstützt."
        )

    @staticmethod
    def _digits(
        tax_number: str,
    ) -> str:
        """Entfernt übliche Darstellungstrennzeichen."""

        normalized = re.sub(
            r"[\s/-]",
            "",
            tax_number,
        )

        if not normalized.isdigit():
            raise ValueError(
                "Steuernummer darf nur Ziffern und "
                "übliche Trennzeichen enthalten."
            )

        return normalized

    @classmethod
    def _normalize_two_digit_office_state(
        cls,
        *,
        federal_state: str,
        tax_number: str,
    ) -> str:
        """Normalisiert Länder mit zweistelliger Finanzamtsnummer."""

        if len(tax_number) != 10:
            raise ValueError(
                "Ungültige Steuernummer für das Bundesland."
            )

        finanzamt = tax_number[:2]
        bezirk = tax_number[2:5]
        unterscheidung_und_pruefziffer = tax_number[5:]

        return (
            cls._TWO_DIGIT_OFFICE_PREFIXES[federal_state]
            + finanzamt
            + "0"
            + bezirk
            + unterscheidung_und_pruefziffer
        )

    @classmethod
    def _normalize_three_digit_office_state(
        cls,
        *,
        federal_state: str,
        tax_number: str,
    ) -> str:
        """Normalisiert Länder mit dreistelliger Finanzamtsnummer."""

        if len(tax_number) != 11:
            raise ValueError(
                "Ungültige Steuernummer für das Bundesland."
            )

        finanzamt = tax_number[:3]
        bezirk = tax_number[3:6]
        unterscheidung_und_pruefziffer = tax_number[6:]

        return (
            cls._THREE_DIGIT_OFFICE_PREFIXES[federal_state]
            + finanzamt
            + "0"
            + bezirk
            + unterscheidung_und_pruefziffer
        )

    @staticmethod
    def _normalize_hesse(
        tax_number: str,
    ) -> str:
        """Normalisiert eine hessische Steuernummer."""

        if (
            len(tax_number) != 11
            or not tax_number.startswith("0")
        ):
            raise ValueError(
                "Ungültige Steuernummer für Hessen."
            )

        finanzamt = tax_number[1:3]
        bezirk = tax_number[3:6]
        unterscheidung_und_pruefziffer = tax_number[6:]

        return (
            "26"
            + finanzamt
            + "0"
            + bezirk
            + unterscheidung_und_pruefziffer
        )

    @staticmethod
    def _normalize_north_rhine_westphalia(
        tax_number: str,
    ) -> str:
        """Normalisiert eine nordrhein-westfälische Steuernummer."""

        if len(tax_number) != 11:
            raise ValueError(
                "Ungültige Steuernummer für Nordrhein-Westfalen."
            )

        finanzamt = tax_number[:3]
        bezirk = tax_number[3:7]
        unterscheidung_und_pruefziffer = tax_number[7:]

        return (
            "5"
            + finanzamt
            + "0"
            + bezirk
            + unterscheidung_und_pruefziffer
        )
