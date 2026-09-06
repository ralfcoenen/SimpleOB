"""Vorbereitung der ELSTER-Nutzdatenhülle aus SimpleOB-Daten."""

from __future__ import annotations

from datetime import date

from openbilanz.core.version import get_application_version
from openbilanz.domain.company_master_data import CompanyMasterData
from openbilanz.domain.tax_number_normalizer import TaxNumberNormalizer
from openbilanz.eric.elster_bilanz_payload import (
    ElsterBilanzPayloadBuilder,
    ElsterBilanzPayloadData,
)

PRODUCT_NAME = "SimpleOB"


class ElsterBilanzPayloadService:
    """Erzeugt einen ELSTER-DatenTeil für eine SimpleOB-E-Bilanz."""

    def __init__(
        self,
        builder: ElsterBilanzPayloadBuilder | None = None,
        tax_number_normalizer: TaxNumberNormalizer | None = None,
    ) -> None:
        self._builder = builder or ElsterBilanzPayloadBuilder()
        self._tax_number_normalizer = (
            tax_number_normalizer or TaxNumberNormalizer()
        )

    def build(
        self,
        *,
        xbrl_xml: str,
        master_data: CompanyMasterData,
        balance_sheet_date: date,
        data_supplier: str | None = None,
    ) -> str:
        tax_number_13 = self._tax_number_normalizer.normalize(
            federal_state=master_data.federal_state,
            tax_number=master_data.tax_number,
        )

        tax_office_number = tax_number_13[:4]

        data = ElsterBilanzPayloadData(
            balance_sheet_date=balance_sheet_date,
            tax_office_number=tax_office_number,
            product_name=PRODUCT_NAME,
            product_version=get_application_version(),
            data_supplier=data_supplier,
        )

        return self._builder.build(
            xbrl_xml=xbrl_xml,
            data=data,
        )
