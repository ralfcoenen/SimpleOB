"""Tests für FiscalYearWorkspace."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import ANY, Mock
from uuid import uuid4

import pytest

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.core.context import ApplicationContext
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.journal import Journal
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.e_bilanz_export_service import (
    EBilanzExportService,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.posting_service import PostingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
    TaxonomyStatus,
)
from openbilanz.taxonomy.arelle_adapter import (
    ArelleValidationResult,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


@pytest.fixture
def company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Test UG",
    )


@pytest.fixture
def fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


@pytest.fixture
def context(
    company: Company,
    fiscal_year: FiscalYear,
) -> ApplicationContext:
    return ApplicationContext(
        company=company,
        fiscal_year=fiscal_year,
    )


def test_reconstructs_empty_workspace(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert isinstance(workspace.journal, Journal)
    assert isinstance(workspace.ledger, Ledger)
    assert isinstance(
        workspace.pre_closing_ledger,
        Ledger,
    )
    assert len(workspace.journal) == 0

    booking_repository.list_for_fiscal_year.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
    )


def test_reports_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert workspace.is_open is True
    assert workspace.is_closed is False


def test_reports_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert workspace.is_open is False
    assert workspace.is_closed is True

def test_reports_taxonomy_status_for_opened_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    taxonomy_management_service = Mock(
        spec=TaxonomyManagementService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    expected_status = TaxonomyStatus(
        required_version=TaxonomyVersion.V6_9,
        installed=True,
        complete=True,
    )

    taxonomy_management_service.status_for.return_value = (
        expected_status
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=(
            taxonomy_management_service
        ),
        e_bilanz_export_service=Mock(),
    )

    status = workspace.taxonomy_status

    assert status is expected_status

    taxonomy_management_service.status_for.assert_called_once_with(
        context.fiscal_year
    )

def test_raises_when_managed_fiscal_year_is_missing(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()
    company_repository.get_managed_fiscal_years.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Das geöffnete Geschäftsjahr wurde nicht gefunden.",
    ):
        _ = workspace.managed_fiscal_year


def test_post_booking_persists_and_reloads_workspace(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    closing_workflow = Mock()

    posting_service = PostingService()

    booking = Booking(
        booking_date=date(2026, 3, 15),
        voucher_no="B-001",
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    booking_repository.list_for_fiscal_year.side_effect = (
        (),
        (booking,),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert len(workspace.journal) == 0

    workspace.post_booking(booking)

    booking_repository.add.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
        booking=booking,
    )

    assert len(workspace.journal) == 1
    assert tuple(workspace.journal) == (booking,)

    account = workspace.ledger.get_account("1200")

    assert account.debit == Decimal("100.00")
    assert account.credit == Decimal("0.00")


def test_post_booking_does_not_change_workspace_when_persistence_fails(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    closing_workflow = Mock()

    posting_service = PostingService()

    booking_repository.list_for_fiscal_year.return_value = ()
    booking_repository.add.side_effect = ValueError(
        "Das Geschäftsjahr ist abgeschlossen."
    )

    booking = Booking(
        booking_date=date(2026, 3, 15),
        voucher_no="B-002",
        description="Nicht zulässige Buchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("50.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("50.00"),
            ),
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Das Geschäftsjahr ist abgeschlossen.",
    ):
        workspace.post_booking(booking)

    assert len(workspace.journal) == 0

    with pytest.raises(KeyError):
        workspace.ledger.get_account("1200")

    booking_repository.list_for_fiscal_year.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
    )


def test_close_fiscal_year_uses_workflow_and_reloads_closed_bookings(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    posting_service = PostingService()
    closing_workflow = Mock()

    original_booking = Booking(
        booking_date=date(2026, 6, 1),
        voucher_no="R-001",
        description="Erlös",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    closing_booking = Booking(
        booking_date=date(2026, 12, 31),
        voucher_no=None,
        description="Abschluss des Erlöskontos 8400",
        lines=(
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="8990",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
        booking_type=BookingType.CLOSING,
    )

    closing_result = ClosingResult(
        net_income=Decimal("500.00"),
        bookings=(closing_booking,),
    )

    closing_workflow.close.return_value = closing_result

    booking_repository.list_for_fiscal_year.side_effect = (
        (original_booking,),
        (
            original_booking,
            closing_booking,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    income_statement = Mock(
        spec=IncomeStatement
    )
    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    result = workspace.close_fiscal_year(
        income_statement=income_statement,
        chart_of_accounts=chart_of_accounts,
    )

    assert result is closing_result

    closing_workflow.close.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
        income_statement=income_statement,
        ledger=ANY,
        chart_of_accounts=chart_of_accounts,
        closing_date=context.fiscal_year.end_date,
    )

    assert len(workspace.journal) == 2
    assert tuple(workspace.journal) == (
        original_booking,
        closing_booking,
    )

    revenue_account = workspace.ledger.get_account(
        "8400"
    )

    assert revenue_account.debit == Decimal("500.00")
    assert revenue_account.credit == Decimal("500.00")

    closing_account = workspace.ledger.get_account(
        "8990"
    )


    assert closing_account.credit == Decimal("500.00")

    pre_closing_revenue_account = (
        workspace.pre_closing_ledger.get_account(
            "8400"
        )
    )

    assert (
        pre_closing_revenue_account.debit
        == Decimal("0.00")
    )
    assert (
        pre_closing_revenue_account.credit
        == Decimal("500.00")
    )

    with pytest.raises(KeyError):
        workspace.pre_closing_ledger.get_account(
            "8990"
        )


def test_validate_closing_delegates_to_consistency_service(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    expected_result = ClosingConsistencyResult(
        errors=()
    )

    closing_consistency_service.validate.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    balance_sheet = Mock(
        spec=BalanceSheet
    )

    income_statement = Mock(
        spec=IncomeStatement
    )

    closing_result = ClosingResult(
        net_income=Decimal("100.00")
    )

    balances: tuple[AccountBalance, ...] = ()

    mapper = Mock(
        spec=AccountMapper
    )

    result = workspace.validate_closing(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        closing_result=closing_result,
        balances=balances,
        mapper=mapper,
    )

    assert result is expected_result

    closing_consistency_service.validate.assert_called_once()

    call_kwargs = (
        closing_consistency_service
        .validate
        .call_args
        .kwargs
    )

    assert call_kwargs["balance_sheet"] is balance_sheet
    assert call_kwargs["income_statement"] is income_statement
    assert call_kwargs["closing_result"] is closing_result
    assert call_kwargs["balances"] == balances
    assert call_kwargs["mapper"] is mapper
    assert call_kwargs["trial_balance"].ledger is workspace.ledger

def test_loads_company_master_data(
    context: ApplicationContext,
) -> None:
    """Die Stammdaten des geöffneten Unternehmens werden geladen."""

    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_office="Finanzamt Musterstadt",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    company_repository.get_master_data.return_value = (
        master_data
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    result = workspace.load_company_master_data()

    assert result is master_data

    company_repository.get_master_data.assert_called_once_with(
        context.company.company_id
    )


def test_saves_company_master_data(
    context: ApplicationContext,
) -> None:
    """Die Stammdaten des geöffneten Unternehmens werden gespeichert."""

    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_office="Finanzamt Musterstadt",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    workspace.save_company_master_data(
        master_data
    )

    company_repository.save_master_data.assert_called_once_with(
        master_data
    )

def test_prepares_e_bilanz_for_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    expected_result = Mock()

    preparation_service.prepare.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    income_statement = Mock(
        spec=IncomeStatement
    )

    result = workspace.prepare_e_bilanz(
        income_statement=income_statement,
    )

    assert result is expected_result

    preparation_service.prepare.assert_called_once_with(
        income_statement=income_statement,
        closed_ledger=workspace.ledger,
    )

def test_rejects_e_bilanz_preparation_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Die E-Bilanz kann erst nach dem "
            "Jahresabschluss vorbereitet werden."
        ),
    ):
        workspace.prepare_e_bilanz(
            income_statement=Mock(
                spec=IncomeStatement
            ),
        )

def test_builds_e_bilanz_from_prepared_data(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    previous_fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=previous_fiscal_year,
        ),
    )

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
    )

    company_repository.get_master_data.return_value = (
        master_data
    )

    preparation = Mock()
    preparation.amounts = {
        Mock(): Decimal("100.00"),
    }

    expected_document = Mock()
    e_bilanz_service.build.return_value = (
        expected_document
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    previous_document = Mock(
        spec=EBilanzDocument
    )
    workspace._validated_e_bilanz_document = (
        previous_document
    )

    result = workspace.build_e_bilanz(
        preparation=preparation,
    )

    assert result is expected_document

    assert workspace._validated_e_bilanz_document is None

    e_bilanz_service.build.assert_called_once_with(
        master_data=master_data,
        fiscal_year=context.fiscal_year,
        amounts=preparation.amounts,
        entity_identifier=str(
            context.company.company_id
        ),
        entity_scheme="urn:openbilanz:company-id",
        previous_fiscal_year=previous_fiscal_year,
    )

def test_rejects_e_bilanz_build_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Die E-Bilanz kann erst nach dem "
            "Jahresabschluss erzeugt werden."
        ),
    ):
        workspace.build_e_bilanz(
            preparation=Mock(),
        )

def test_validates_e_bilanz_for_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    expected_result = ArelleValidationResult(
        is_valid=True,
        errors=(),
    )

    e_bilanz_service.validate.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    result = workspace.validate_e_bilanz(
        document
    )

    assert result is expected_result

    e_bilanz_service.validate.assert_called_once_with(
        document,
        fiscal_year=context.fiscal_year,
    )

def test_rejects_e_bilanz_validation_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    with pytest.raises(
        ValueError,
        match=(
            "E-Bilanz kann erst nach dem "
            "Jahresabschluss validiert werden"
        ),
    ):
        workspace.validate_e_bilanz(
            document
        )

def test_installs_required_taxonomy_for_opened_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    taxonomy_management_service = Mock(
        spec=TaxonomyManagementService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        taxonomy_management_service=(
            taxonomy_management_service
        ),
        e_bilanz_export_service=Mock(),
    )

    workspace.install_required_taxonomy()

    taxonomy_management_service.install_required_taxonomy.assert_called_once_with(
        context.fiscal_year
    )

def test_exports_successfully_validated_e_bilanz(
    context: ApplicationContext,
    tmp_path: Path,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    e_bilanz_service = Mock()
    export_service = Mock(
        spec=EBilanzExportService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    validation_result = ArelleValidationResult(
        is_valid=True,
        errors=(),
    )
    e_bilanz_service.validate.return_value = validation_result

    document = Mock(
        spec=EBilanzDocument
    )
    target = tmp_path / "e-bilanz.xbrl"

    export_service.export.return_value = target

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_export_service=export_service,
        taxonomy_management_service=Mock(),
    )

    workspace.validate_e_bilanz(
        document
    )

    result = workspace.export_e_bilanz(
        document=document,
        target=target,
    )

    assert result == target

    export_service.export.assert_called_once_with(
        document=document,
        target=target,
    )


def test_rejects_export_of_unvalidated_e_bilanz(
    context: ApplicationContext,
    tmp_path: Path,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    export_service = Mock(
        spec=EBilanzExportService
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_export_service=export_service,
        taxonomy_management_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    with pytest.raises(
        ValueError,
        match=(
            "E-Bilanz muss vor dem Export "
            "erfolgreich validiert werden"
        ),
    ):
        workspace.export_e_bilanz(
            document=document,
            target=tmp_path / "e-bilanz.xbrl",
        )

    export_service.export.assert_not_called()
