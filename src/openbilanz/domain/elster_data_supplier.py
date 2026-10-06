"""Daten des Erstellers einer ELSTER-Übermittlung."""

from __future__ import annotations

from dataclasses import dataclass

MAX_ELSTER_DATA_SUPPLIER_LENGTH = 256


@dataclass(frozen=True, slots=True)
class ElsterDataSupplier:
    """Beschreibt den Ersteller einer E-Bilanz."""

    name: str = ""
    street: str = ""
    house_number: str = ""
    house_number_suffix: str = ""
    address_addition: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    email: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "name",
            "street",
            "house_number",
            "house_number_suffix",
            "address_addition",
            "postal_code",
            "city",
            "country",
            "phone",
            "email",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} muss eine Zeichenkette sein."
                )

            normalized = value.strip()

            if ";" in normalized:
                raise ValueError(
                    f"{field_name} darf kein Semikolon enthalten."
                )

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        if (
            self.is_configured
            and len(self.to_eric_value())
            > MAX_ELSTER_DATA_SUPPLIER_LENGTH
        ):
            raise ValueError(
                "Die Daten des ELSTER-Datenlieferanten "
                "dürfen zusammen höchstens "
                f"{MAX_ELSTER_DATA_SUPPLIER_LENGTH} Zeichen umfassen."
            )

    @property
    def is_configured(self) -> bool:
        """Zeigt an, ob Daten zum Ersteller hinterlegt sind."""

        return any(
            (
                self.name,
                self.street,
                self.house_number,
                self.house_number_suffix,
                self.address_addition,
                self.postal_code,
                self.city,
                self.country,
                self.phone,
                self.email,
            )
        )

    def to_eric_value(self) -> str:
        """Erzeugt den von ERiC erwarteten DatenLieferant-Wert."""

        return "; ".join(
            (
                self.name,
                self.street,
                self.house_number,
                self.house_number_suffix,
                self.address_addition,
                self.postal_code,
                self.city,
                self.country,
                self.phone,
                self.email,
            )
        )
