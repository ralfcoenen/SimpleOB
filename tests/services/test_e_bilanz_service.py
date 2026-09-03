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
from openbilanz.domain.shareholder import Shareholder
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
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderLegalStatus,
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
            shareholders=(
                shareholder,
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
        gcd_namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2025-04-01"
        ),
        gaap_ci_namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2025-04-01"
        ),
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
        == "5123045678901"
    )
    assert (
        call_kwargs["identifiers"].tax_number_13
        == "5123045678901"
    )

    assert call_kwargs["shareholders"] == (
        GcdShareholder(
            name="Muster",
            first_name="Max",
            shareholder_id="1",
            tax_number=None,
            tax_id="12345678901",
            wid=None,
            legal_status=(
                GcdShareholderLegalStatus.NATURAL_PERSON
            ),
            share_divide_key=GcdShareDivideKey(
                numerator="1",
                denominator="2",
            ),
        ),
    )


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
