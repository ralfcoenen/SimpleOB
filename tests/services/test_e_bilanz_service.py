"""Tests für EBilanzService."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.shareholder import Shareholder
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.taxonomy.arelle_adapter import (
    ArelleValidationResult,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
)
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


class FakeResolver:
    """Minimaler Resolver für den E-Bilanz-Service-Test."""

    def __init__(
        self,
        *,
        gcd_path: Path,
        gaap_ci_path: Path,
    ) -> None:
        self.gcd_path = gcd_path
        self.gaap_ci_path = gaap_ci_path

        self.received_gcd_version = None
        self.received_gaap_ci_version = None

    def gcd_entry_point(
        self,
        version: TaxonomyVersion,
    ) -> Path:
        self.received_gcd_version = version
        return self.gcd_path

    def gaap_ci_fiscal_entry_point(
        self,
        version: TaxonomyVersion,
    ) -> Path:
        self.received_gaap_ci_version = version
        return self.gaap_ci_path


class FakeAdapter:
    """Minimaler Arelle-Adapter für den E-Bilanz-Service-Test."""

    def __init__(
        self,
        *,
        gcd_model: object,
        gaap_ci_model: object,
    ) -> None:
        self._gcd_model = gcd_model
        self._gaap_ci_model = gaap_ci_model

        self.received_paths: list[Path] = []
        self.validated_path: Path | None = None
        self.validated_content: str | None = None

    def model(
        self,
        entry_point: Path,
    ) -> object:
        self.received_paths.append(
            entry_point
        )

        if len(self.received_paths) == 1:
            return self._gcd_model

        return self._gaap_ci_model

    def validate(
        self,
        entry_point: Path,
    ) -> ArelleValidationResult:
        """Simuliert die Validierung einer erzeugten XBRL-Datei."""

        self.validated_path = entry_point
        self.validated_content = entry_point.read_text(
            encoding="utf-8",
        )

        return ArelleValidationResult(
            is_valid=True,
            errors=(),
        )


def _company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Muster UG",
    )

def test_e_bilanz_service_orchestrates_builder() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    company = _company()

    master_data = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="123/4567/8901",
        federal_state="NW",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="1",
        postal_code="50667",
        city="Köln",
        country="DE",
        business="Softwareentwicklung",
    )

    shareholder = Shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="",
        tax_id="12345678901",
        wid="",
    )

    vat_accounts = Mock(
        spec=VatAccounts
    )
    vat_accounts.input_tax_7 = "1571"
    vat_accounts.input_tax_19 = "1576"
    vat_accounts.output_tax_7 = "1771"
    vat_accounts.output_tax_19 = "1776"

    account_roles = Mock(
        spec=AccountingAccountRoles
    )
    account_roles.cash_accounts = frozenset(
        {"1000"}
    )
    account_roles.bank_accounts = frozenset(
        {"1200"}
    )
    account_roles.general_rate_sales_accounts = frozenset(
        {"8400"}
    )

    gcd_path = Path("/tmp/gcd.xsd")
    gaap_ci_path = Path("/tmp/gaap-ci.xsd")

    resolver = FakeResolver(
        gcd_path=gcd_path,
        gaap_ci_path=gaap_ci_path,
    )

    gcd_model = Mock()
    gcd_model.concepts.concepts = ()

    gaap_ci_model = Mock()
    gaap_ci_model.concepts.concepts = ()

    adapter = FakeAdapter(
        gcd_model=gcd_model,
        gaap_ci_model=gaap_ci_model,
    )

    assets = Mock(
        spec=FinancialStatementPosition
    )
    liabilities = Mock(
        spec=FinancialStatementPosition
    )
    income_statement_root = Mock(
        spec=FinancialStatementPosition
    )

    prepared_income_statement = Mock(
        spec=IncomeStatement
    )
    prepared_income_statement.income_statement = (
        income_statement_root
    )

    prepared_balance_sheet = Mock(
        spec=BalanceSheet
    )
    prepared_balance_sheet.assets = assets
    prepared_balance_sheet.liabilities = liabilities

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_path,
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2025-04-01/shell"
        ),
        schema_imports=(),
    )

    gaap_ci_entry_point = TaxonomyEntryPoint(
        path=gaap_ci_path,
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2025-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    amounts: dict[
        FinancialStatementPosition,
        Decimal,
    ] = {}

    service = EBilanzService(
        resolver=resolver,  # type: ignore[arg-type]
        adapter=adapter,  # type: ignore[arg-type]
        company_data_mapper=GcdCompanyDataMapper(),
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement_root,
    )

    profile = Mock()
    profile.fact_plan = Mock()

    concepts = Mock()
    resolved_fact_plan = Mock()
    resolved_fact_plan.nodes = ()

    closing_service = Mock()
    closing_service.calculate_net_income.return_value = (
        Decimal("100.00")
    )

    gaap_ci_values = Mock()

    balance_sheet_values = {
        ("bs.test",): Decimal("100.00"),
    }

    income_statement_values = {
        ("is.test",): Decimal("100.00"),
    }

    account_detail_values = {
        ("ks.test",): Decimal("100.00"),
    }

    gcd_fact_builder = Mock()
    shareholder_tuple = Mock()
    gcd_fact_builder.shareholder.return_value = (
        shareholder_tuple
    )

    mandatory_completer = Mock()
    mandatory_completer.build_missing_nil_facts.return_value = ()

    requirement_reader = Mock()
    requirement_reader.requirements.return_value = ()

    document_builder = Mock()
    document_builder.build_xml.return_value = (
        "<xbrl />"
    )

    taxonomy_mapper = Mock()
    account_balance_builder = Mock()

    with (
        patch(
            "openbilanz.services.e_bilanz_service."
            "TaxonomyEntryPoint.from_file",
            side_effect=(
                gcd_entry_point,
                gaap_ci_entry_point,
            ),
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "TaxonomyConceptSet",
            return_value=concepts,
        ) as concept_set_class,
        patch(
            "openbilanz.services.e_bilanz_service."
            "ClosingService",
            return_value=closing_service,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "GaapCi69ValueCalculator.calculate",
            return_value=gaap_ci_values,
        ) as gaap_ci_calculate,
        patch(
            "openbilanz.services.e_bilanz_service."
            "create_profile_6_9",
            return_value=profile,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "GaapCi69BalanceSheetValueBuilder.build",
            return_value=balance_sheet_values,
        ) as balance_sheet_builder,
        patch(
            "openbilanz.services.e_bilanz_service."
            "GaapCi69IncomeStatementValueBuilder.build",
            return_value=income_statement_values,
        ) as income_statement_builder,
        patch(
            "openbilanz.services.e_bilanz_service."
            "GaapCi69AccountDetailValueBuilder.build",
            return_value=account_detail_values,
        ) as account_detail_builder,
        patch(
            "openbilanz.services.e_bilanz_service."
            "Taxonomy69ValueBuilder.build",
            return_value={},
        ) as value_builder,
        patch(
            "openbilanz.services.e_bilanz_service."
            "FactPlanResolver.resolve",
            return_value=resolved_fact_plan,
        ) as fact_plan_resolver,
        patch(
            "openbilanz.services.e_bilanz_service."
            "FiscalRequirementReader",
            return_value=requirement_reader,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "GaapCiMandatoryFactCompleter",
            return_value=mandatory_completer,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "GcdFactBuilder",
            return_value=gcd_fact_builder,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "create_hgb_gaap_ci_mapping",
            return_value=Mock(),
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "TaxonomyMapper",
            return_value=taxonomy_mapper,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "AccountBalanceBuilder",
            return_value=account_balance_builder,
        ),
        patch(
            "openbilanz.services.e_bilanz_service."
            "Taxonomy69XbrlDocumentBuilder",
            return_value=document_builder,
        ),
    ):
        document = service.build(
            master_data=master_data,
            fiscal_year=fiscal_year,
            amounts=amounts,
            income_statement=prepared_income_statement,
            balance_sheet=prepared_balance_sheet,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            entity_identifier="1234567890123",
            entity_scheme=(
                "http://www.rzf-nrw.de/Steuernummer"
            ),
            account_details=(),
            fixed_asset_schedule=(),
            shareholders=(shareholder,),
        )

    assert isinstance(
        document,
        EBilanzDocument,
    )

    assert document.xml == "<xbrl />"

    concept_set_class.assert_called_once_with(
        concepts=(
            gcd_model.concepts.concepts
            + gaap_ci_model.concepts.concepts
        )
    )

    closing_service.calculate_net_income.assert_called_once_with(
        income_statement=prepared_income_statement,
    )

    gaap_ci_calculate.assert_called_once_with(
        income_statement=prepared_income_statement,
        net_income=Decimal("100.00"),
    )

    balance_sheet_builder.assert_called_once_with(
        balance_sheet=prepared_balance_sheet,
        income_statement=income_statement_root,
    )

    income_statement_builder.assert_called_once_with(
        income_statement=prepared_income_statement,
        assets=assets,
        liabilities=liabilities,
        fixed_asset_schedule=(),
    )

    account_detail_builder.assert_called_once_with(
        account_details=(),
        tax_liability_accounts=(
            "1771",
            "1776",
        ),
        general_rate_sales_accounts=frozenset(
            {"8400"}
        ),
        cash_accounts=frozenset(
            {"1000"}
        ),
        bank_accounts=frozenset(
            {"1200"}
        ),
        input_tax_receivable_accounts=(
            "1571",
            "1576",
        ),
    )

    value_builder.assert_called_once()

    fact_plan_resolver.assert_called_once()

    gcd_fact_builder.shareholder.assert_called_once()

    mandatory_completer.build_missing_nil_facts.assert_called_once()

    account_balance_builder.build.assert_not_called()

    document_builder.build_xml.assert_called_once()

def test_e_bilanz_service_validates_document_with_relative_schema_refs(
    tmp_path: Path,
    ) -> None:
    """Für die Offline-Validierung werden relative schemaRefs verwendet."""

    taxonomy_root = (
        tmp_path
        / "taxonomy root with spaces"
        / "6.9"
    )

    gcd_directory = (
        taxonomy_root
        / "de-gcd-2025-04-01"
    )
    gaap_ci_directory = (
        taxonomy_root
        / "de-gaap-ci-2025-04-01"
    )

    gcd_directory.mkdir(
        parents=True
    )
    gaap_ci_directory.mkdir(
        parents=True
    )

    gcd_path = (
        gcd_directory
        / "de-gcd-2025-04-01-shell.xsd"
    )

    gaap_ci_path = (
        gaap_ci_directory
        / "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    gcd_path.write_text(
        (
            '<xs:schema '
            'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'targetNamespace='
            '"http://www.xbrl.de/taxonomies/'
            'de-gcd-2025-04-01/shell">'
            "</xs:schema>"
        ),
        encoding="utf-8",
    )

    gaap_ci_path.write_text(
        (
            '<xs:schema '
            'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'targetNamespace='
            '"http://www.xbrl.de/taxonomies/'
            'de-gaap-ci-2025-04-01/shell-fiscal">'
            "</xs:schema>"
        ),
        encoding="utf-8",
    )

    resolver = FakeResolver(
        gcd_path=gcd_path,
        gaap_ci_path=gaap_ci_path,
    )

    adapter = FakeAdapter(
        gcd_model=object(),
        gaap_ci_model=object(),
    )

    service = EBilanzService(
        resolver=resolver,  # type: ignore[arg-type]
        adapter=adapter,  # type: ignore[arg-type]
        company_data_mapper=GcdCompanyDataMapper(),
        assets=Mock(
            spec=FinancialStatementPosition
        ),
        liabilities=Mock(
            spec=FinancialStatementPosition
        ),
        income_statement=Mock(
            spec=FinancialStatementPosition
        ),
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    gcd_schema_ref_uri = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01/"
        "de-gcd-2025-04-01-shell.xsd"
    )

    gaap_ci_schema_ref_uri = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    original_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<xbrl xmlns:link="http://www.xbrl.org/2003/linkbase" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<link:schemaRef '
        'xlink:type="simple" '
        f'xlink:href="{gcd_schema_ref_uri}"/>'
        '<link:schemaRef '
        'xlink:type="simple" '
        f'xlink:href="{gaap_ci_schema_ref_uri}"/>'
        "</xbrl>"
    )

    document = EBilanzDocument(
        xml=original_xml,
        gaap_ci_statement=Mock(),
    )

    result = service.validate(
        document,
        fiscal_year=fiscal_year,
    )

    assert result.is_valid
    assert result.errors == ()

    assert adapter.validated_path is not None
    assert adapter.validated_content is not None

    assert (
        adapter.validated_path.parent.parent
        == taxonomy_root
    )

    gcd_relative_path = (
        "../de-gcd-2025-04-01/"
        "de-gcd-2025-04-01-shell.xsd"
    )

    gaap_ci_relative_path = (
        "../de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    assert (
        gcd_relative_path
        in adapter.validated_content
    )

    assert (
        gaap_ci_relative_path
        in adapter.validated_content
    )

    assert (
        gcd_schema_ref_uri
        not in adapter.validated_content
    )

    assert (
        gaap_ci_schema_ref_uri
        not in adapter.validated_content
    )

    assert "file://" not in adapter.validated_content

    assert str(tmp_path) not in adapter.validated_content

    # Das eigentliche Exportdokument bleibt unverändert.
    assert document.xml == original_xml


def test_e_bilanz_document_does_not_require_legacy_gaap_ci_statement() -> None:
    document = EBilanzDocument(
        xml="<xbrl/>",
    )

    assert document.xml == "<xbrl/>"
    assert document.gaap_ci_statement is None
