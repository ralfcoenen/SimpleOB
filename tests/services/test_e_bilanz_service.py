"""Tests für EBilanzService."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.services.e_bilanz_service import EBilanzService
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

    master_data = CompanyMasterData(
        company=_company(),
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
    )

    gcd_path = Path("/tmp/gcd.xsd")
    gaap_ci_path = Path("/tmp/gaap-ci.xsd")

    resolver = FakeResolver(
        gcd_path=gcd_path,
        gaap_ci_path=gaap_ci_path,
    )

    gcd_model = object()
    gaap_ci_model = object()

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
    income_statement = Mock(
        spec=FinancialStatementPosition
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_path,
        namespace="urn:test:gcd",
        schema_imports=(),
    )

    gaap_ci_entry_point = TaxonomyEntryPoint(
        path=gaap_ci_path,
        namespace="urn:test:gaap-ci",
        schema_imports=(),
    )

    expected_document = Mock(
        spec=EBilanzDocument
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
        income_statement=income_statement,
    )

    builder = Mock()
    builder.build.return_value = (
        expected_document
    )

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
            "EBilanzBuilder",
            return_value=builder,
        ) as builder_class,
    ):
        result = service.build(
            master_data=master_data,
            fiscal_year=fiscal_year,
            amounts=amounts,
            entity_identifier="DE123456789",
            entity_scheme=(
                "http://www.bundesfinanzministerium.de"
            ),
        )

    assert result is expected_document

    assert (
        resolver.received_gcd_version
        is TaxonomyVersion.V6_9
    )
    assert (
        resolver.received_gaap_ci_version
        is TaxonomyVersion.V6_9
    )

    assert adapter.received_paths == [
        gcd_path,
        gaap_ci_path,
    ]

    builder_class.assert_called_once_with(
        gcd_model=gcd_model,
        gaap_ci_model=gaap_ci_model,
        gcd_entry_point=gcd_entry_point,
        gaap_ci_entry_point=gaap_ci_entry_point,
        gcd_namespace="urn:test:gcd",
        gaap_ci_namespace="urn:test:gaap-ci",
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )

    builder.build.assert_called_once()

    call_kwargs = (
        builder.build.call_args.kwargs
    )

    assert (
        call_kwargs["fiscal_year"]
        is fiscal_year
    )
    assert call_kwargs["amounts"] is amounts
    assert (
        call_kwargs["entity_identifier"]
        == "DE123456789"
    )
    assert (
        call_kwargs["entity_scheme"]
        == "http://www.bundesfinanzministerium.de"
    )

    assert (
        call_kwargs["company_data"].company
        == master_data.company
    )
    assert (
        call_kwargs["company_data"].tax_number
        == master_data.tax_number
    )
    assert (
        call_kwargs["identifiers"].tax_number_13
        == master_data.tax_number
    )

