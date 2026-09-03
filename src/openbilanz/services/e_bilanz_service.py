"""Anwendungsservice zur Erzeugung einer E-Bilanz."""

import os
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.shareholder import Shareholder
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.arelle_adapter import (
    ArelleAdapter,
    ArelleValidationResult,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzBuilder,
    EBilanzDocument,
)
from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
)
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderLegalStatus,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import (
    taxonomy_version_for,
)


class EBilanzService:
    """Erzeugt eine E-Bilanz aus produktiven Anwendungsdaten."""

    def __init__(
        self,
        *,
        resolver: TaxonomyResolver,
        adapter: ArelleAdapter,
        company_data_mapper: GcdCompanyDataMapper,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
    ) -> None:
        self._resolver = resolver
        self._adapter = adapter
        self._company_data_mapper = company_data_mapper
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement

    def build(
        self,
        *,
        master_data: CompanyMasterData,
        fiscal_year: FiscalYear,
        amounts: Mapping[
            FinancialStatementPosition,
            Decimal,
        ],
        entity_identifier: str,
        entity_scheme: str,
        previous_fiscal_year: FiscalYear | None = None,
        account_details: tuple[
            EBilanzAccountDetail,
            ...
        ] = (),
        fixed_asset_schedule: tuple[
            FixedAssetSchedulePosition,
            ...
        ] = (),
        shareholders: tuple[
            Shareholder,
            ...
        ] = (),
    ) -> EBilanzDocument:
        """Erzeugt die E-Bilanz-XBRL-Instanz."""

        mapping = self._company_data_mapper.map(
            master_data
        )

        version = taxonomy_version_for(
            fiscal_year
        )

        gcd_path = self._resolver.gcd_entry_point(
            version
        )

        gaap_ci_path = (
            self._resolver.gaap_ci_fiscal_entry_point(
                version
            )
        )

        gcd_entry_point = (
            TaxonomyEntryPoint.from_file(
                gcd_path
            )
        )

        gaap_ci_entry_point = (
            TaxonomyEntryPoint.from_file(
                gaap_ci_path
            )
        )

        gcd_model = self._adapter.model(
            gcd_path
        )

        gaap_ci_model = self._adapter.model(
            gaap_ci_path
        )

        gcd_namespace = (
            gcd_entry_point.namespace
            .removesuffix("/shell")
        )

        gaap_ci_namespace = (
            gaap_ci_entry_point.namespace
            .removesuffix("/shell-fiscal")
        )

        builder = EBilanzBuilder(
            gcd_model=gcd_model,
            gaap_ci_model=gaap_ci_model,
            gcd_entry_point=gcd_entry_point,
            gaap_ci_entry_point=gaap_ci_entry_point,
            gcd_namespace=gcd_namespace,
            gaap_ci_namespace=gaap_ci_namespace,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )
        gcd_shareholders = tuple(
            self._map_shareholder(
                shareholder
            )
            for shareholder in shareholders
        )

        return builder.build(
            company_data=mapping.company_data,
            fiscal_year=fiscal_year,
            amounts=amounts,
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            previous_fiscal_year=previous_fiscal_year,
            identifiers=mapping.identifiers,
            account_details=account_details,
            fixed_asset_schedule=fixed_asset_schedule,
            shareholders=gcd_shareholders,
        )

    @staticmethod
    def _map_shareholder(
        shareholder: Shareholder,
    ) -> GcdShareholder:
        """Überführt produktive Gesellschafterdaten in GCD-Daten."""

        if not isinstance(
            shareholder,
            Shareholder,
        ):
            raise TypeError(
                "shareholder must be a Shareholder"
            )

        return GcdShareholder(
            name=shareholder.name,
            first_name=(
                shareholder.first_name
                or None
            ),
            shareholder_id=(
                shareholder.shareholder_number
            ),
            tax_number=(
                shareholder.tax_number
                or None
            ),
            tax_id=(
                shareholder.tax_id
                or None
            ),
            wid=(
                shareholder.wid
                or None
            ),
            legal_status=(
                GcdShareholderLegalStatus(
                    shareholder.legal_status
                )
            ),
            share_divide_key=(
                GcdShareDivideKey(
                    numerator=(
                        shareholder.share_numerator
                    ),
                    denominator=(
                        shareholder.share_denominator
                    ),
                )
            ),
        )

    def validate(
        self,
        document: EBilanzDocument,
        *,
        fiscal_year: FiscalYear,
    ) -> ArelleValidationResult:
        """Validiert eine erzeugte E-Bilanz mit Arelle."""

        if not isinstance(
            document,
            EBilanzDocument,
        ):
            raise TypeError(
                "document muss ein EBilanzDocument sein."
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year muss ein FiscalYear sein."
            )

        version = taxonomy_version_for(
            fiscal_year
        )

        gcd_path = self._resolver.gcd_entry_point(
            version
        )

        gaap_ci_path = (
            self._resolver.gaap_ci_fiscal_entry_point(
                version
            )
        )

        gcd_entry_point = TaxonomyEntryPoint.from_file(
            gcd_path
        )

        gaap_ci_entry_point = TaxonomyEntryPoint.from_file(
            gaap_ci_path
        )

        taxonomy_root = Path(
            os.path.commonpath(
                (
                    gcd_path.parent,
                    gaap_ci_path.parent,
                )
            )
        )

        with TemporaryDirectory(
            prefix="openbilanz-e-bilanz-",
            dir=taxonomy_root,
        ) as temporary_directory:
            temporary_directory_path = Path(
                temporary_directory
            )

            gcd_relative_path = Path(
                os.path.relpath(
                    gcd_path,
                    temporary_directory_path,
                )
            ).as_posix()

            gaap_ci_relative_path = Path(
                os.path.relpath(
                    gaap_ci_path,
                    temporary_directory_path,
                )
            ).as_posix()

            validation_xml = document.xml

            validation_xml = validation_xml.replace(
                gcd_entry_point.schema_ref_uri,
                gcd_relative_path,
            )

            validation_xml = validation_xml.replace(
                gaap_ci_entry_point.schema_ref_uri,
                gaap_ci_relative_path,
            )

            instance_path = (
                temporary_directory_path
                / "openbilanz-e-bilanz.xbrl"
            )

            instance_path.write_text(
                validation_xml,
                encoding="utf-8",
            )

            return self._adapter.validate(
                instance_path
            )
