"""Unternehmensstammdaten für die GCD-Taxonomie."""

from dataclasses import dataclass

from openbilanz.domain.company import Company


@dataclass(frozen=True, slots=True)
class GcdCompanyData:
    """Enthält Unternehmensstammdaten für die E-Bilanz."""

    company: Company
    tax_number: str
    legal_form: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.company,
            Company,
        ):
            raise TypeError(
                "company must be a Company"
            )

        if not isinstance(
            self.tax_number,
            str,
        ):
            raise TypeError(
                "tax_number must be a string"
            )

        if not self.tax_number.strip():
            raise ValueError(
                "tax_number must not be blank"
            )

        if (
            len(self.tax_number) != 13
            or not self.tax_number.isdigit()
        ):
            raise ValueError(
                "tax_number must contain exactly 13 digits"
            )


        if not isinstance(
            self.legal_form,
            str,
        ):
            raise TypeError(
                "legal_form must be a string"
            )

        if not self.legal_form.strip():
            raise ValueError(
                "legal_form must not be blank"
            )
            
