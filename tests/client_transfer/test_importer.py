"""Tests für den portablen Mandantenimport."""

from datetime import date, datetime, timezone
from uuid import UUID
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.client_transfer.importer import (
    ClientTransferImporter,
)
from openbilanz.client_transfer.model import (
    CLIENT_TRANSFER_FORMAT_NAME,
    CLIENT_TRANSFER_FORMAT_VERSION,
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferBookingLineReference,
    ClientTransferFixedAssetDepreciation,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferFixedAssetMovement,
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFixedAsset,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferShareholder,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
)
from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.database.shareholder_repository import (
    ShareholderRepository,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from openbilanz.domain.company import Company
from openbilanz.domain.depreciation_kind import DepreciationKind
from openbilanz.domain.depreciation_source import DepreciationSource
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import (
    FiscalYearStatus,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)



COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)


def _build_position_provider(
) -> HgbFinancialStatementPositionProvider:
    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Guthaben bei Kreditinstituten",
    )

    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(bank_position,),
    )

    return HgbFinancialStatementPositionProvider(
        (assets,)
    )


def _build_transfer() -> ClientTransfer:
    return ClientTransfer(
        format=ClientTransferFormat(
            name=CLIENT_TRANSFER_FORMAT_NAME,
            version=CLIENT_TRANSFER_FORMAT_VERSION,
        ),
        application=ClientTransferApplication(
            name="SimpleOB",
            version="0.46.0",
        ),
        exported_at=datetime(
            2026,
            10,
            3,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Import Test UG",
                legal_form="UG (haftungsbeschränkt)",
                tax_number="123/456/78901",
                tax_office="Testfinanzamt",
                street="Teststraße",
                house_number="1",
                postal_code="40210",
                city="Düsseldorf",
                country="Deutschland",
                federal_state="NW",
                business="Softwareentwicklung",
            ),
            accounts=(
                ClientTransferAccount(
                    account_number="1000",
                    name="Kasse",
                    account_type="ASSET",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="1200",
                    name="Bank",
                    account_type="ASSET",
                    is_active=True,
                    debit_position_code=(
                        "HGB.266.AKTIVA.B.IV"
                    ),
                ),
                ClientTransferAccount(
                    account_number="1571",
                    name="Vorsteuer 7 %",
                    account_type="ASSET",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="1576",
                    name="Vorsteuer 19 %",
                    account_type="ASSET",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="1771",
                    name="Umsatzsteuer 7 %",
                    account_type="LIABILITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="1776",
                    name="Umsatzsteuer 19 %",
                    account_type="LIABILITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="0755",
                    name="Ausschüttungsverbindlichkeit",
                    account_type="LIABILITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="0846",
                    name="Gesetzliche Rücklage",
                    account_type="EQUITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="0855",
                    name="Andere Gewinnrücklagen",
                    account_type="EQUITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="2970",
                    name="Gewinn-/Verlustvortrag",
                    account_type="EQUITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="4830",
                    name="Abschreibungen",
                    account_type="EXPENSE",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="4900",
                    name="Anlagenabgang Gewinn",
                    account_type="REVENUE",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="8020",
                    name="Gewinnkonto",
                    account_type="EQUITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="8021",
                    name="Verlustkonto",
                    account_type="EQUITY",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="8500",
                    name="Anlagenabgang Verlust",
                    account_type="EXPENSE",
                    is_active=True,
                ),
                ClientTransferAccount(
                    account_number="9000",
                    name="Saldenvorträge",
                    account_type="EQUITY",
                    is_active=True,
                ),
            ),
            control_accounts=ClientTransferControlAccounts(
                opening_balance_account="9000",
                income_summary_account="8020",
                profit_account="8020",
                loss_account="8021",
                profit_loss_carryforward_account="2970",
                statutory_reserve_account="0846",
                other_revenue_reserves_account="0855",
                distribution_liability_account="0755",
                depreciation_expense_account="4830",
                fixed_asset_disposal_gain_account="4900",
                fixed_asset_disposal_loss_account="8500",
            ),
            vat_accounts=ClientTransferVatAccounts(
                input_tax_7="1571",
                input_tax_19="1576",
                output_tax_7="1771",
                output_tax_19="1776",
            ),
            account_roles=ClientTransferAccountRoles(
                cash_accounts=("1000",),
                bank_accounts=("1200",),
            ),
            taxonomy_mappings=(
                ClientTransferTaxonomyMapping(
                    taxonomy_version="6.9",
                    account_number="1000",
                    concept_name=(
                        "bs.ass.currAss.cashEquiv.cash"
                    ),
                ),
                ClientTransferTaxonomyMapping(
                    taxonomy_version="test-version-2",
                    account_number="1200",
                    concept_name="test.bank",
                ),
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=date(2025, 7, 1),
                    end_date=date(2026, 6, 30),
                    status="CLOSED",
                    opening_source=None,
                ),
                ClientTransferFiscalYear(
                    start_date=date(2026, 7, 1),
                    end_date=date(2027, 6, 30),
                    status="OPEN",
                    opening_source=(
                        ClientTransferFiscalYearReference(
                            start_date=date(
                                2025,
                                7,
                                1,
                            ),
                            end_date=date(
                                2026,
                                6,
                                30,
                            ),
                        )
                    ),
                ),
            ),
        ),
    )


def test_importer_restores_client_base_data() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        booking_repository = BookingRepository(
            session
        )

        shareholder_repository = ShareholderRepository(
            session
        )

        fixed_asset_repository = FixedAssetRepository(
            session
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=shareholder_repository,
            fixed_asset_repository=fixed_asset_repository,
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=_build_transfer(),
            position_provider=(
                _build_position_provider()
            ),
        )

        master_data = (
            company_repository.get_master_data(
                COMPANY_ID
            )
        )

        (
            chart_of_accounts,
            accounts,
        ) = chart_repository.load_for_company(
            company_id=COMPANY_ID,
            position_provider=(
                _build_position_provider()
            ),
        )

        control_accounts = (
            chart_repository.load_control_accounts(
                COMPANY_ID
            )
        )
        vat_accounts = (
            chart_repository.load_vat_accounts(
                COMPANY_ID
            )
        )
        account_roles = (
            chart_repository.load_account_roles(
                COMPANY_ID
            )
        )
        taxonomy_mappings = (
            chart_repository
            .load_all_account_taxonomy_concepts(
                COMPANY_ID
            )
        )

        managed_fiscal_years = (
            company_repository
            .get_managed_fiscal_years(
                COMPANY_ID
            )
        )

    assert master_data is not None
    assert master_data.company.name == (
        "Import Test UG"
    )
    assert master_data.legal_form == (
        "UG (haftungsbeschränkt)"
    )
    assert master_data.city == "Düsseldorf"

    account_by_number = {
        account.number: account
        for account in accounts
    }

    assert account_by_number["1200"].name == "Bank"
    assert (
        account_by_number["1200"].is_active
        is True
    )

    mapping_by_number = {
        rule.account_number: rule
        for rule
        in chart_of_accounts.account_mapping_rules
    }

    assert (
        mapping_by_number[
            "1200"
        ].debit_position.code
        == "HGB.266.AKTIVA.B.IV"
    )
    assert (
        mapping_by_number[
            "1200"
        ].credit_position
        is None
    )

    assert (
        control_accounts
        .profit_loss_carryforward_account
        == "2970"
    )
    assert vat_accounts.output_tax_19 == "1776"

    assert account_roles.cash_accounts == frozenset(
        {"1000"}
    )
    assert account_roles.bank_accounts == frozenset(
        {"1200"}
    )

    assert taxonomy_mappings == {
        "6.9": {
            "1000": (
                "bs.ass.currAss.cashEquiv.cash"
            ),
        },
        "test-version-2": {
            "1200": "test.bank",
        },
    }

    assert len(managed_fiscal_years) == 2

    first_year = managed_fiscal_years[0]
    second_year = managed_fiscal_years[1]

    assert first_year.status == (
        FiscalYearStatus.CLOSED
    )
    assert first_year.opening_source is None

    assert second_year.status == (
        FiscalYearStatus.OPEN
    )
    assert second_year.opening_source == (
        first_year.fiscal_year
    )


def test_importer_rejects_existing_company_id() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        booking_repository = BookingRepository(
            session
        )

        shareholder_repository = ShareholderRepository(
            session
        )

        fixed_asset_repository = FixedAssetRepository(
            session
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        existing_company = Company(
            company_id=COMPANY_ID,
            name="Bestehender Mandant",
        )
        company_repository.add(
            existing_company
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=shareholder_repository,
            fixed_asset_repository=fixed_asset_repository,
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            )
        )

        with pytest.raises(
            ValueError,
            match="company_id",
        ):
            importer.import_transfer(
                transfer=_build_transfer(),
                position_provider=(
                    _build_position_provider()
                ),
            )

        loaded_company = company_repository.get(
            COMPANY_ID
        )

        chart_data = (
            chart_repository.load_for_company(
                company_id=COMPANY_ID,
                position_provider=(
                    _build_position_provider()
                ),
            )
        )

    assert loaded_company == existing_company
    assert chart_data is None


def test_importer_rolls_back_complete_import_on_error(
) -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        booking_repository = BookingRepository(
            session
        )

        shareholder_repository = ShareholderRepository(
            session
        )

        fixed_asset_repository = FixedAssetRepository(
            session
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=shareholder_repository,
            fixed_asset_repository=fixed_asset_repository,
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            )
        )

        position_provider = (
            _build_position_provider()
        )

        original_get = position_provider.get

        def failing_get(
            code: str,
        ) -> FinancialStatementPosition:
            if code == "HGB.266.AKTIVA.B.IV":
                raise RuntimeError(
                    "Absichtlicher Importfehler"
                )

            return original_get(code)

        position_provider.get = failing_get

        with pytest.raises(
            RuntimeError,
            match="Absichtlicher Importfehler",
        ):
            importer.import_transfer(
                transfer=_build_transfer(),
                position_provider=position_provider,
            )

        assert (
            company_repository.get(
                COMPANY_ID
            )
            is None
        )


def test_importer_restores_booking_and_reversal() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    original_booking_id = UUID(
        "11111111-1111-1111-1111-111111111111"
    )
    reversal_booking_id = UUID(
        "22222222-2222-2222-2222-222222222222"
    )

    base_transfer = _build_transfer()

    first_fiscal_year = (
        base_transfer.client.fiscal_years[0]
    )
    second_fiscal_year = (
        base_transfer.client.fiscal_years[1]
    )

    reversal_booking = ClientTransferBooking(
        booking_id=reversal_booking_id,
        booking_date=date(2026, 2, 2),
        booking_type="REVERSAL",
        voucher_no="ST-1",
        description="Storno Testbuchung",
        reversal_of_booking_id=original_booking_id,
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="CREDIT",
                amount="123.45",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1000",
                side="DEBIT",
                amount="123.45",
            ),
        ),
    )

    original_booking = ClientTransferBooking(
        booking_id=original_booking_id,
        booking_date=date(2026, 2, 1),
        booking_type="REGULAR",
        voucher_no="B-1",
        description="Testbuchung",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="DEBIT",
                amount="123.45",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1000",
                side="CREDIT",
                amount="123.45",
            ),
        ),
    )

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=base_transfer.client.shareholders,
            fixed_assets=base_transfer.client.fixed_assets,
            profit_appropriation_annual_data=(
                base_transfer.client
                .profit_appropriation_annual_data
            ),
            profit_appropriation_postings=(
                base_transfer.client
                .profit_appropriation_postings
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=first_fiscal_year.start_date,
                    end_date=first_fiscal_year.end_date,
                    status=first_fiscal_year.status,
                    opening_source=(
                        first_fiscal_year.opening_source
                    ),
                    bookings=(
                        reversal_booking,
                        original_booking,
                    ),
                ),
                second_fiscal_year,
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )
        booking_repository = BookingRepository(
            session
        )

        shareholder_repository = ShareholderRepository(
            session
        )

        fixed_asset_repository = FixedAssetRepository(
            session
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=shareholder_repository,
            fixed_asset_repository=fixed_asset_repository,
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        loaded_original = booking_repository.get(
            original_booking_id
        )
        loaded_reversal = booking_repository.get(
            reversal_booking_id
        )

        managed_fiscal_years = (
            company_repository
            .get_managed_fiscal_years(
                COMPANY_ID
            )
        )

    assert loaded_original is not None
    assert loaded_original.booking_id == (
        original_booking_id
    )
    assert loaded_original.booking_type is (
        BookingType.REGULAR
    )
    assert loaded_original.voucher_no == "B-1"
    assert loaded_original.description == (
        "Testbuchung"
    )

    assert len(loaded_original.lines) == 2
    assert (
        loaded_original.lines[0].account_number
        == "1200"
    )
    assert (
        loaded_original.lines[0].side
        is EntrySide.DEBIT
    )
    assert str(
        loaded_original.lines[0].amount
    ) == "123.45"

    assert loaded_reversal is not None
    assert loaded_reversal.booking_id == (
        reversal_booking_id
    )
    assert loaded_reversal.booking_type is (
        BookingType.REVERSAL
    )
    assert loaded_reversal.reversal_of_booking_id == (
        original_booking_id
    )

    assert len(loaded_reversal.lines) == 2
    assert (
        loaded_reversal.lines[0].account_number
        == "1200"
    )
    assert (
        loaded_reversal.lines[0].side
        is EntrySide.CREDIT
    )

    assert managed_fiscal_years[0].status is (
        FiscalYearStatus.CLOSED
    )


def test_importer_restores_shareholder() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    shareholder_id = UUID(
        "33333333-3333-3333-3333-333333333333"
    )

    base_transfer = _build_transfer()

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=(
                ClientTransferShareholder(
                    shareholder_id=shareholder_id,
                    shareholder_number="1",
                    name="Mustermann",
                    first_name="Max",
                    legal_status="NATURAL_PERSON",
                    share_numerator="1",
                    share_denominator="2",
                    tax_number="1234567890123",
                    tax_number_federal_state="NW",
                    tax_id="12345678901",
                    wid="",
                ),
            ),
            fiscal_years=base_transfer.client.fiscal_years,
            fixed_assets=base_transfer.client.fixed_assets,
            profit_appropriation_annual_data=(
                base_transfer.client
                .profit_appropriation_annual_data
            ),
            profit_appropriation_postings=(
                base_transfer.client
                .profit_appropriation_postings
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )
        booking_repository = BookingRepository(
            session
        )
        shareholder_repository = (
            ShareholderRepository(
                session
            )
        )

        fixed_asset_repository = (
            FixedAssetRepository(
                session
            )
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=(
                shareholder_repository
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        shareholders = (
            shareholder_repository.list_for_company(
                COMPANY_ID
            )
        )

    assert len(shareholders) == 1

    shareholder = shareholders[0]

    assert shareholder.shareholder_id == (
        shareholder_id
    )
    assert shareholder.company_id == COMPANY_ID
    assert shareholder.shareholder_number == "1"
    assert shareholder.name == "Mustermann"
    assert shareholder.first_name == "Max"
    assert shareholder.legal_status == (
        "NATURAL_PERSON"
    )
    assert shareholder.share_numerator == "1"
    assert shareholder.share_denominator == "2"
    assert shareholder.tax_number == (
        "1234567890123"
    )
    assert (
        shareholder.tax_number_federal_state
        == "NW"
    )
    assert shareholder.tax_id == "12345678901"
    assert shareholder.wid == ""


def test_importer_restores_fixed_asset() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    fixed_asset_id = UUID(
        "44444444-4444-4444-4444-444444444444"
    )

    base_transfer = _build_transfer()

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=base_transfer.client.shareholders,
            fixed_assets=(
                ClientTransferFixedAsset(
                    fixed_asset_id=fixed_asset_id,
                    asset_code="BGA-001",
                    description="Notebook",
                    position_code=(
                        "HGB.266.AKTIVA.A.II.3"
                    ),
                    asset_account_number="1200",
                    depreciation_expense_account_number=(
                        "1000"
                    ),
                    acquisition_date=date(
                        2025,
                        8,
                        15,
                    ),
                    acquisition_cost="1200.00",
                    depreciation_start_date=date(
                        2025,
                        8,
                        15,
                    ),
                    useful_life_months=36,
                    status="ACTIVE",
                ),
            ),
            profit_appropriation_annual_data=(
                base_transfer.client
                .profit_appropriation_annual_data
            ),
            profit_appropriation_postings=(
                base_transfer.client
                .profit_appropriation_postings
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
            fiscal_years=base_transfer.client.fiscal_years,
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )
        booking_repository = BookingRepository(
            session
        )
        shareholder_repository = (
            ShareholderRepository(
                session
            )
        )
        fixed_asset_repository = (
            FixedAssetRepository(
                session
            )
        )

        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=(
                shareholder_repository
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        fixed_assets = (
            fixed_asset_repository.list_for_company(
                COMPANY_ID
            )
        )

    assert len(fixed_assets) == 1

    fixed_asset = fixed_assets[0]

    assert fixed_asset.fixed_asset_id == fixed_asset_id
    assert fixed_asset.company_id == COMPANY_ID
    assert fixed_asset.asset_code == "BGA-001"
    assert fixed_asset.description == "Notebook"
    assert (
        fixed_asset.position_code
        == "HGB.266.AKTIVA.A.II.3"
    )
    assert fixed_asset.asset_account_number == "1200"
    assert (
        fixed_asset.depreciation_expense_account_number
        == "1000"
    )
    assert fixed_asset.acquisition_date == date(
        2025,
        8,
        15,
    )
    assert fixed_asset.acquisition_cost == Decimal(
        "1200.00"
    )
    assert fixed_asset.depreciation_start_date == date(
        2025,
        8,
        15,
    )
    assert fixed_asset.useful_life_months == 36
    assert fixed_asset.status is FixedAssetStatus.ACTIVE
    assert fixed_asset.disposal_date is None


def test_importer_restores_fixed_asset_movements() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    original_booking_id = UUID(
        "11111111-1111-1111-1111-111111111111"
    )
    reversal_booking_id = UUID(
        "22222222-2222-2222-2222-222222222222"
    )
    fixed_asset_id = UUID(
        "44444444-4444-4444-4444-444444444444"
    )
    original_movement_id = UUID(
        "55555555-5555-5555-5555-555555555555"
    )
    reversal_movement_id = UUID(
        "66666666-6666-6666-6666-666666666666"
    )

    base_transfer = _build_transfer()

    first_fiscal_year = (
        base_transfer.client.fiscal_years[0]
    )
    second_fiscal_year = (
        base_transfer.client.fiscal_years[1]
    )

    reversal_booking = ClientTransferBooking(
        booking_id=reversal_booking_id,
        booking_date=date(2026, 2, 2),
        booking_type="REVERSAL",
        voucher_no="ST-1",
        description="Storno Anlagenzugang",
        reversal_of_booking_id=original_booking_id,
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="CREDIT",
                amount="123.45",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1000",
                side="DEBIT",
                amount="123.45",
            ),
        ),
    )

    original_booking = ClientTransferBooking(
        booking_id=original_booking_id,
        booking_date=date(2026, 2, 1),
        booking_type="REGULAR",
        voucher_no="B-1",
        description="Anlagenzugang",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="DEBIT",
                amount="123.45",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1000",
                side="CREDIT",
                amount="123.45",
            ),
        ),
    )

    fixed_asset = ClientTransferFixedAsset(
        fixed_asset_id=fixed_asset_id,
        asset_code="BGA-001",
        description="Notebook",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="1200",
        depreciation_expense_account_number="1000",
        acquisition_date=date(2026, 2, 1),
        acquisition_cost="123.45",
        depreciation_start_date=date(2026, 2, 1),
        useful_life_months=36,
        status="ACTIVE",
        movements=(
            # Absichtlich Storno zuerst:
            ClientTransferFixedAssetMovement(
                movement_id=reversal_movement_id,
                fiscal_year_end=first_fiscal_year.end_date,
                movement_date=date(2026, 2, 2),
                amount="123.45",
                booking_line=(
                    ClientTransferBookingLineReference(
                        booking_id=reversal_booking_id,
                        position=0,
                    )
                ),
                movement_type="REVERSAL",
                reversed_movement_id=original_movement_id,
            ),
            ClientTransferFixedAssetMovement(
                movement_id=original_movement_id,
                fiscal_year_end=first_fiscal_year.end_date,
                movement_date=date(2026, 2, 1),
                amount="123.45",
                booking_line=(
                    ClientTransferBookingLineReference(
                        booking_id=original_booking_id,
                        position=0,
                    )
                ),
                movement_type="ACQUISITION",
            ),
        ),
    )

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=base_transfer.client.shareholders,
            fixed_assets=(
                fixed_asset,
            ),
            profit_appropriation_annual_data=(
                base_transfer.client
                .profit_appropriation_annual_data
            ),
            profit_appropriation_postings=(
                base_transfer.client
                .profit_appropriation_postings
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=first_fiscal_year.start_date,
                    end_date=first_fiscal_year.end_date,
                    status=first_fiscal_year.status,
                    opening_source=(
                        first_fiscal_year.opening_source
                    ),
                    bookings=(
                        reversal_booking,
                        original_booking,
                    ),
                ),
                second_fiscal_year,
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = (
            ChartOfAccountsRepository(
                session
            )
        )
        booking_repository = BookingRepository(
            session
        )
        shareholder_repository = (
            ShareholderRepository(
                session
            )
        )
        fixed_asset_repository = (
            FixedAssetRepository(
                session
            )
        )
        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )

        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=(
                shareholder_repository
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        loaded_original = (
            fixed_asset_movement_repository.get(
                original_movement_id
            )
        )
        loaded_reversal = (
            fixed_asset_movement_repository.get(
                reversal_movement_id
            )
        )

    assert loaded_original is not None
    assert loaded_original.movement_id == (
        original_movement_id
    )
    assert loaded_original.fixed_asset_id == (
        fixed_asset_id
    )
    assert loaded_original.fiscal_year_end == (
        first_fiscal_year.end_date
    )
    assert loaded_original.movement_date == date(
        2026,
        2,
        1,
    )
    assert loaded_original.amount == Decimal(
        "123.45"
    )
    assert loaded_original.booking_id == (
        original_booking_id
    )
    assert loaded_original.movement_type is (
        FixedAssetMovementType.ACQUISITION
    )
    assert loaded_original.reversed_movement_id is None

    assert loaded_reversal is not None
    assert loaded_reversal.movement_id == (
        reversal_movement_id
    )
    assert loaded_reversal.fixed_asset_id == (
        fixed_asset_id
    )
    assert loaded_reversal.fiscal_year_end == (
        first_fiscal_year.end_date
    )
    assert loaded_reversal.movement_date == date(
        2026,
        2,
        2,
    )
    assert loaded_reversal.amount == Decimal(
        "123.45"
    )
    assert loaded_reversal.booking_id == (
        reversal_booking_id
    )
    assert loaded_reversal.movement_type is (
        FixedAssetMovementType.REVERSAL
    )
    assert loaded_reversal.reversed_movement_id == (
        original_movement_id
    )


def test_importer_restores_fixed_asset_depreciation_with_tax_adjustment(
) -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    depreciation_booking_id = UUID(
        "77777777-7777-7777-7777-777777777777"
    )
    fixed_asset_id = UUID(
        "44444444-4444-4444-4444-444444444444"
    )
    depreciation_id = UUID(
        "88888888-8888-8888-8888-888888888888"
    )

    base_transfer = _build_transfer()

    first_fiscal_year = (
        base_transfer.client.fiscal_years[0]
    )
    second_fiscal_year = (
        base_transfer.client.fiscal_years[1]
    )

    depreciation_booking = ClientTransferBooking(
        booking_id=depreciation_booking_id,
        booking_date=date(2026, 3, 31),
        booking_type="REGULAR",
        voucher_no="AFA-1",
        description="Abschreibung Notebook",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1000",
                side="DEBIT",
                amount="40.00",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1200",
                side="CREDIT",
                amount="40.00",
            ),
        ),
    )

    depreciation = ClientTransferFixedAssetDepreciation(
        depreciation_id=depreciation_id,
        fiscal_year_end=first_fiscal_year.end_date,
        depreciation_date=date(2026, 3, 31),
        amount="40.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=depreciation_booking_id,
            position=0,
        ),
        kind="LINEAR",
        source="CALCULATED",
        tax_adjustment=(
            ClientTransferTaxDepreciationAdjustment(
                depreciation_id=depreciation_id,
                tax_amount="50.00",
            )
        ),
    )

    fixed_asset = ClientTransferFixedAsset(
        fixed_asset_id=fixed_asset_id,
        asset_code="BGA-001",
        description="Notebook",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="1200",
        depreciation_expense_account_number="1000",
        acquisition_date=date(2025, 8, 15),
        acquisition_cost="1200.00",
        depreciation_start_date=date(2025, 8, 15),
        useful_life_months=36,
        status="ACTIVE",
        depreciations=(
            depreciation,
        ),
    )

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=base_transfer.client.shareholders,
            fixed_assets=(
                fixed_asset,
            ),
            profit_appropriation_annual_data=(
                base_transfer.client
                .profit_appropriation_annual_data
            ),
            profit_appropriation_postings=(
                base_transfer.client
                .profit_appropriation_postings
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=first_fiscal_year.start_date,
                    end_date=first_fiscal_year.end_date,
                    status=first_fiscal_year.status,
                    opening_source=(
                        first_fiscal_year.opening_source
                    ),
                    bookings=(
                        depreciation_booking,
                    ),
                ),
                second_fiscal_year,
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = ChartOfAccountsRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        shareholder_repository = ShareholderRepository(
            session
        )
        fixed_asset_repository = FixedAssetRepository(
            session
        )
        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )
        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )
        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=(
                shareholder_repository
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        loaded_depreciation = (
            fixed_asset_depreciation_repository.get(
                depreciation_id
            )
        )
        loaded_adjustment = (
            tax_depreciation_adjustment_repository
            .get_for_depreciation(
                depreciation_id
            )
        )

    assert loaded_depreciation is not None
    assert loaded_depreciation.depreciation_id == (
        depreciation_id
    )
    assert loaded_depreciation.fixed_asset_id == (
        fixed_asset_id
    )
    assert loaded_depreciation.fiscal_year_end == (
        first_fiscal_year.end_date
    )
    assert loaded_depreciation.depreciation_date == date(
        2026,
        3,
        31,
    )
    assert loaded_depreciation.amount == Decimal(
        "40.00"
    )
    assert loaded_depreciation.booking_id == (
        depreciation_booking_id
    )
    assert loaded_depreciation.kind is (
        DepreciationKind.LINEAR
    )
    assert loaded_depreciation.source is (
        DepreciationSource.CALCULATED
    )

    assert loaded_adjustment is not None
    assert loaded_adjustment.depreciation_id == (
        depreciation_id
    )
    assert loaded_adjustment.commercial_amount == Decimal(
        "40.00"
    )
    assert loaded_adjustment.tax_amount == Decimal(
        "50.00"
    )
    assert loaded_adjustment.difference == Decimal(
        "10.00"
    )


def test_importer_restores_profit_appropriation_data_and_posting(
) -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    posting_booking_id = UUID(
        "99999999-9999-9999-9999-999999999999"
    )
    posting_id = UUID(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )

    base_transfer = _build_transfer()

    first_fiscal_year = (
        base_transfer.client.fiscal_years[0]
    )
    second_fiscal_year = (
        base_transfer.client.fiscal_years[1]
    )

    source_fiscal_year_reference = (
        ClientTransferFiscalYearReference(
            start_date=first_fiscal_year.start_date,
            end_date=first_fiscal_year.end_date,
        )
    )

    annual_data = (
        ClientTransferProfitAppropriationAnnualData(
            fiscal_year=source_fiscal_year_reference,
            statutory_reserve_addition="100.00",
            other_revenue_reserves_addition="0.00",
            statutory_reserve_release="0.00",
            other_revenue_reserves_release="0.00",
            distribution="0.00",
            profit_loss_carryforward="900.00",
        )
    )

    posting_booking = ClientTransferBooking(
        booking_id=posting_booking_id,
        booking_date=date(2026, 7, 15),
        booking_type="REGULAR",
        voucher_no="GV-1",
        description="Zuführung gesetzliche Rücklage",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="2970",
                side="DEBIT",
                amount="100.00",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="0846",
                side="CREDIT",
                amount="100.00",
            ),
        ),
    )

    posting = ClientTransferProfitAppropriationPosting(
        posting_id=posting_id,
        source_fiscal_year=source_fiscal_year_reference,
        posting_date=date(2026, 7, 15),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=posting_booking_id,
            position=0,
        ),
        posting_type="STATUTORY_RESERVE_ADDITION",
    )

    transfer = ClientTransfer(
        format=base_transfer.format,
        application=base_transfer.application,
        exported_at=base_transfer.exported_at,
        client=ClientTransferClient(
            company_id=base_transfer.client.company_id,
            master_data=base_transfer.client.master_data,
            accounts=base_transfer.client.accounts,
            control_accounts=(
                base_transfer.client.control_accounts
            ),
            vat_accounts=base_transfer.client.vat_accounts,
            account_roles=base_transfer.client.account_roles,
            taxonomy_mappings=(
                base_transfer.client.taxonomy_mappings
            ),
            shareholders=base_transfer.client.shareholders,
            fixed_assets=base_transfer.client.fixed_assets,
            profit_appropriation_annual_data=(
                annual_data,
            ),
            profit_appropriation_postings=(
                posting,
            ),
            equity_contributions=(
                base_transfer.client.equity_contributions
            ),
            fiscal_years=(
                first_fiscal_year,
                ClientTransferFiscalYear(
                    start_date=second_fiscal_year.start_date,
                    end_date=second_fiscal_year.end_date,
                    status=second_fiscal_year.status,
                    opening_source=(
                        second_fiscal_year.opening_source
                    ),
                    bookings=(
                        posting_booking,
                    ),
                ),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        chart_repository = ChartOfAccountsRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        shareholder_repository = ShareholderRepository(
            session
        )
        fixed_asset_repository = FixedAssetRepository(
            session
        )
        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(
                session
            )
        )
        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )
        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )
        profit_appropriation_annual_data_repository = (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        )
        profit_appropriation_posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        importer = ClientTransferImporter(
            company_repository=company_repository,
            chart_of_accounts_repository=(
                chart_repository
            ),
            booking_repository=booking_repository,
            shareholder_repository=(
                shareholder_repository
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            profit_appropriation_annual_data_repository=(
                profit_appropriation_annual_data_repository
            ),
            profit_appropriation_posting_repository=(
                profit_appropriation_posting_repository
            ),
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=(
                _build_position_provider()
            ),
        )

        loaded_annual_data = (
            profit_appropriation_annual_data_repository
            .get_for_fiscal_year(
                company_id=base_transfer.client.company_id,
                fiscal_year=FiscalYear(
                    start_date=first_fiscal_year.start_date,
                    end_date=first_fiscal_year.end_date,
                ),
            )
        )

        loaded_posting = (
            profit_appropriation_posting_repository.get(
                posting_id
            )
        )

    assert loaded_annual_data is not None
    assert (
        loaded_annual_data.statutory_reserve_addition
        == Decimal("100.00")
    )
    assert (
        loaded_annual_data.other_revenue_reserves_addition
        == Decimal("0.00")
    )
    assert (
        loaded_annual_data.statutory_reserve_release
        == Decimal("0.00")
    )
    assert (
        loaded_annual_data.other_revenue_reserves_release
        == Decimal("0.00")
    )
    assert loaded_annual_data.distribution == Decimal(
        "0.00"
    )
    assert (
        loaded_annual_data.profit_loss_carryforward
        == Decimal("900.00")
    )

    assert loaded_posting is not None
    assert loaded_posting.posting_id == posting_id
    assert loaded_posting.source_fiscal_year_end == (
        first_fiscal_year.end_date
    )
    assert loaded_posting.posting_date == date(
        2026,
        7,
        15,
    )
    assert loaded_posting.amount == Decimal(
        "100.00"
    )
    assert loaded_posting.booking_id == (
        posting_booking_id
    )
    assert loaded_posting.posting_type is (
        ProfitAppropriationPostingType
        .STATUTORY_RESERVE_ADDITION
    )
