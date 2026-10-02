"""Unternehmensstammdaten."""

from dataclasses import dataclass

from openbilanz.domain.company import Company
from openbilanz.domain.tax_number_normalizer import (
    TaxNumberNormalizer,
)

GERMAN_FEDERAL_STATE_CODES = frozenset(
    {
        "BW",
        "BY",
        "BE",
        "BB",
        "HB",
        "HH",
        "HE",
        "MV",
        "NI",
        "NW",
        "RP",
        "SL",
        "SN",
        "ST",
        "SH",
        "TH",
    }
)

LEGAL_FORM_SOLE_PROPRIETORSHIP_GBR = "Einzelunternehmen/GbR"
LEGAL_FORM_UG = "UG (haftungsbeschränkt)"
LEGAL_FORM_GMBH = "GmbH"

SUPPORTED_LEGAL_FORMS = (
    LEGAL_FORM_SOLE_PROPRIETORSHIP_GBR,
    LEGAL_FORM_UG,
    LEGAL_FORM_GMBH,
)

E_BILANZ_LEGAL_FORMS = frozenset(
    {
        LEGAL_FORM_UG,
        LEGAL_FORM_GMBH,
    }
)


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
    federal_state: str = ""
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
            "federal_state",
            self.federal_state,
        )
        self._validate_string(
            "business",
            self.business,
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

        if (
            self.federal_state
            and self.federal_state
            not in GERMAN_FEDERAL_STATE_CODES
        ):
            raise ValueError(
                "federal_state must be a valid German federal state code"
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
    def supports_e_bilanz(self) -> bool:
        """Zeigt, ob die Rechtsform vom E-Bilanz-Pfad unterstützt wird."""

        return self.legal_form in E_BILANZ_LEGAL_FORMS

    @property
    def is_e_bilanz_ready(self) -> bool:
        """Prüft die zwingenden E-Bilanz-Stammdaten."""

        return bool(
            self.supports_e_bilanz
            and self.tax_number
            and self.federal_state
            and self.street
            and self.house_number
            and self.postal_code
            and self.city
            and self.country
            and self.business
        )

    def validate_e_bilanz_ready(self) -> None:
        """Validiert die für die E-Bilanz erforderlichen Stammdaten."""

        if not self.supports_e_bilanz:
            raise ValueError(
                "Die Rechtsform wird vom E-Bilanz-Pfad "
                "nicht unterstützt."
            )

        required_fields = (
            ("Rechtsform", self.legal_form),
            ("Steuernummer", self.tax_number),
            ("Bundesland", self.federal_state),
            ("Straße", self.street),
            ("Hausnummer", self.house_number),
            ("PLZ", self.postal_code),
            ("Ort", self.city),
            ("Land", self.country),
            ("Geschäftstätigkeit", self.business),
        )

        missing_fields = tuple(
            label
            for label, value in required_fields
            if not value
        )

        if missing_fields:
            raise ValueError(
                "Für die E-Bilanz fehlen folgende "
                "Unternehmensstammdaten: "
                + ", ".join(missing_fields)
                + "."
            )

        TaxNumberNormalizer().normalize(
            federal_state=self.federal_state,
            tax_number=self.tax_number,
        )
