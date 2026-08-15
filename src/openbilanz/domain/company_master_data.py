"""Unternehmensstammdaten."""

from dataclasses import dataclass

from openbilanz.domain.company import Company


@dataclass(frozen=True, slots=True)
class CompanyMasterData:
    """Produktive Stammdaten eines Unternehmens."""

    company: Company
    legal_form: str = ""
    tax_number: str = ""
    tax_office: str = ""
    tax_id: str = ""
    tax_economic_id: str = ""
    bf4: str = ""
    street: str = ""
    house_number: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = ""
    business: str = ""

    def __post_init__(self) -> None:
        if not isinstance(
            self.company,
            Company,
        ):
            raise TypeError(
                "company must be a Company"
            )

        self._validate_string(
            "legal_form",
            self.legal_form,
        )
        self._validate_string(
            "tax_number",
            self.tax_number,
        )
        self._validate_string(
            "tax_office",
            self.tax_office,
        )
        self._validate_string(
            "tax_id",
            self.tax_id,
        )
        self._validate_string(
            "tax_economic_id",
            self.tax_economic_id,
        )
        self._validate_string(
            "bf4",
            self.bf4,
        )
        self._validate_string(
            "street",
            self.street,
        )
        self._validate_string(
            "house_number",
            self.house_number,
        )
        self._validate_string(
            "postal_code",
            self.postal_code,
        )
        self._validate_string(
            "city",
            self.city,
        )
        self._validate_string(
            "country",
            self.country,
        )
        self._validate_string(
            "business",
            self.business,
        )

        if (
            self.tax_number
            and (
                len(self.tax_number) != 13
                or not self.tax_number.isdigit()
            )
        ):
            raise ValueError(
                "tax_number must contain exactly 13 digits"
            )

        if (
            self.bf4
            and (
                len(self.bf4) != 4
                or not self.bf4.isdigit()
            )
        ):
            raise ValueError(
                "bf4 must contain exactly 4 digits"
            )

    @staticmethod
    def _validate_string(
        name: str,
        value: str,
    ) -> None:
        """Validiert ein optionales Textfeld."""

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{name} must be a string"
            )

        if value != value.strip():
            raise ValueError(
                f"{name} must not contain surrounding whitespace"
            )

    @property
    def is_e_bilanz_ready(self) -> bool:
        """Prüft die derzeit zwingenden E-Bilanz-Stammdaten."""

        return bool(
            self.legal_form
            and self.tax_number
        )
