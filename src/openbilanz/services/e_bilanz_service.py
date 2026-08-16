"""Anwendungsservice zur Erzeugung einer E-Bilanz."""
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
from openbilanz.domain.fiscal_year import FiscalYear
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

        return builder.build(
            company_data=mapping.company_data,
            fiscal_year=fiscal_year,
            amounts=amounts,
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            previous_fiscal_year=previous_fiscal_year,
            identifiers=mapping.identifiers,
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

        validation_xml = document.xml

        validation_xml = validation_xml.replace(
            gcd_entry_point.schema_ref_uri,
            gcd_path.resolve().as_uri(),
        )

        validation_xml = validation_xml.replace(
            gaap_ci_entry_point.schema_ref_uri,
            gaap_ci_path.resolve().as_uri(),
        )

        with TemporaryDirectory(
            prefix="openbilanz-e-bilanz-"
        ) as temporary_directory:
            instance_path = (
                Path(temporary_directory)
                / "openbilanz-e-bilanz.xbrl"
            )

            instance_path.write_text(
                validation_xml,
                encoding="utf-8",
            )

            return self._adapter.validate(
                instance_path
            )
