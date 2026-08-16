"""Übersetzung produktiver Stammdaten in GCD-Daten."""

from dataclasses import dataclass

from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.tax_number_normalizer import (
    TaxNumberNormalizer,
)
from openbilanz.taxonomy.gcd_company_data import (
    GcdCompanyData,
)
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)


@dataclass(frozen=True, slots=True)
class GcdCompanyDataMapping:
    """Ergebnis der Übersetzung in GCD-Unternehmensdaten."""

    company_data: GcdCompanyData
    identifiers: GcdCompanyIdentifiers


class GcdCompanyDataMapper:
    """Übersetzt Unternehmensstammdaten für die GCD-Taxonomie."""

    def map(
        self,
        master_data: CompanyMasterData,
    ) -> GcdCompanyDataMapping:
        """Erzeugt die GCD-Daten aus produktiven Stammdaten."""

        if not isinstance(
            master_data,
            CompanyMasterData,
        ):
            raise TypeError(
                "master_data must be a CompanyMasterData"
            )

        if not master_data.is_e_bilanz_ready:
            raise ValueError(
                "Die Unternehmensstammdaten sind für "
                "die E-Bilanz noch unvollständig."
            )
            
        tax_number_13 = TaxNumberNormalizer().normalize(
            federal_state=master_data.federal_state,
            tax_number=master_data.tax_number,
        )

        company_data = GcdCompanyData(
            company=master_data.company,
            tax_number=tax_number_13,
            legal_form=master_data.legal_form,
            street=master_data.street,
            house_number=master_data.house_number,
            postal_code=master_data.postal_code,
            city=master_data.city,
            country=master_data.country,
            business=master_data.business,
        )

        identifiers = GcdCompanyIdentifiers(
            tax_number_13=tax_number_13,
            tax_id=(
                master_data.tax_id
                or None
            ),
            tax_economic_id=(
                master_data.tax_economic_id
                or None
            ),
            bf4=(
                master_data.bf4
                or None
            ),
        )

        return GcdCompanyDataMapping(
            company_data=company_data,
            identifiers=identifiers,
        )
    