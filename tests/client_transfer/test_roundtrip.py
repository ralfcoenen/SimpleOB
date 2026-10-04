"""Roundtrip-Tests für den portablen Mandantentransfer."""

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.client_transfer.exporter import (
    ClientTransferExporter,
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
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferEquityContribution,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
    ClientTransferShareholder,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
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
from openbilanz.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
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
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)


COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)

SHAREHOLDER_ID = UUID(
    "33333333-3333-3333-3333-333333333333"
)

FIXED_ASSET_ID = UUID(
    "44444444-4444-4444-4444-444444444444"
)

ACQUISITION_BOOKING_ID = UUID(
    "55555555-5555-5555-5555-555555555555"
)

ACQUISITION_MOVEMENT_ID = UUID(
    "66666666-6666-6666-6666-666666666666"
)

DEPRECIATION_BOOKING_ID = UUID(
    "77777777-7777-7777-7777-777777777777"
)

DEPRECIATION_ID = UUID(
    "88888888-8888-8888-8888-888888888888"
)

PROFIT_POSTING_BOOKING_ID = UUID(
    "99999999-9999-9999-9999-999999999999"
)

PROFIT_POSTING_ID = UUID(
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)

EQUITY_BOOKING_ID = UUID(
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
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


def _build_repositories(
    session: Session,
) -> dict[str, object]:
    return {
        "company_repository": CompanyRepository(
            session
        ),
        "chart_of_accounts_repository": (
            ChartOfAccountsRepository(
                session
            )
        ),
        "booking_repository": BookingRepository(
            session
        ),
        "shareholder_repository": (
            ShareholderRepository(
                session
            )
        ),
        "fixed_asset_repository": (
            FixedAssetRepository(
                session
            )
        ),
        "fixed_asset_movement_repository": (
            FixedAssetMovementRepository(
                session
            )
        ),
        "fixed_asset_depreciation_repository": (
            FixedAssetDepreciationRepository(
                session
            )
        ),
        "tax_depreciation_adjustment_repository": (
            TaxDepreciationAdjustmentRepository(
                session
            )
        ),
        "profit_appropriation_annual_data_repository": (
            ProfitAppropriationAnnualDataRepository(
                session
            )
        ),
        "profit_appropriation_posting_repository": (
            ProfitAppropriationPostingRepository(
                session
            )
        ),
        "equity_contribution_repository": (
            EquityContributionRepository(
                session
            )
        ),
    }


def _build_importer(
    repositories: dict[str, object],
) -> ClientTransferImporter:
    return ClientTransferImporter(
        company_repository=(
            repositories["company_repository"]
        ),
        chart_of_accounts_repository=(
            repositories[
                "chart_of_accounts_repository"
            ]
        ),
        booking_repository=(
            repositories["booking_repository"]
        ),
        shareholder_repository=(
            repositories["shareholder_repository"]
        ),
        fixed_asset_repository=(
            repositories["fixed_asset_repository"]
        ),
        fixed_asset_movement_repository=(
            repositories[
                "fixed_asset_movement_repository"
            ]
        ),
        fixed_asset_depreciation_repository=(
            repositories[
                "fixed_asset_depreciation_repository"
            ]
        ),
        tax_depreciation_adjustment_repository=(
            repositories[
                "tax_depreciation_adjustment_repository"
            ]
        ),
        profit_appropriation_annual_data_repository=(
            repositories[
                "profit_appropriation_annual_data_repository"
            ]
        ),
        profit_appropriation_posting_repository=(
            repositories[
                "profit_appropriation_posting_repository"
            ]
        ),
        equity_contribution_repository=(
            repositories[
                "equity_contribution_repository"
            ]
        ),
    )


def _build_exporter(
    repositories: dict[str, object],
) -> ClientTransferExporter:
    return ClientTransferExporter(
        company_repository=(
            repositories["company_repository"]
        ),
        chart_of_accounts_repository=(
            repositories[
                "chart_of_accounts_repository"
            ]
        ),
        booking_repository=(
            repositories["booking_repository"]
        ),
        shareholder_repository=(
            repositories["shareholder_repository"]
        ),
        fixed_asset_repository=(
            repositories["fixed_asset_repository"]
        ),
        fixed_asset_movement_repository=(
            repositories[
                "fixed_asset_movement_repository"
            ]
        ),
        fixed_asset_depreciation_repository=(
            repositories[
                "fixed_asset_depreciation_repository"
            ]
        ),
        tax_depreciation_adjustment_repository=(
            repositories[
                "tax_depreciation_adjustment_repository"
            ]
        ),
        profit_appropriation_annual_data_repository=(
            repositories[
                "profit_appropriation_annual_data_repository"
            ]
        ),
        profit_appropriation_posting_repository=(
            repositories[
                "profit_appropriation_posting_repository"
            ]
        ),
        equity_contribution_repository=(
            repositories[
                "equity_contribution_repository"
            ]
        ),
    )


def _build_rich_transfer() -> ClientTransfer:
    first_year = ClientTransferFiscalYearReference(
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )

    acquisition_booking = ClientTransferBooking(
        booking_id=ACQUISITION_BOOKING_ID,
        booking_date=date(2026, 2, 1),
        booking_type="REGULAR",
        voucher_no="ANL-1",
        description="Anschaffung Notebook",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="DEBIT",
                amount="1200.00",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1000",
                side="CREDIT",
                amount="1200.00",
            ),
        ),
    )

    depreciation_booking = ClientTransferBooking(
        booking_id=DEPRECIATION_BOOKING_ID,
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

    equity_booking = ClientTransferBooking(
        booking_id=EQUITY_BOOKING_ID,
        booking_date=date(2025, 8, 1),
        booking_type="REGULAR",
        voucher_no="EK-1",
        description="Eigenkapitaleinlage",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1200",
                side="DEBIT",
                amount="500.00",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="2970",
                side="CREDIT",
                amount="500.00",
            ),
        ),
    )

    profit_posting_booking = (
        ClientTransferBooking(
            booking_id=(
                PROFIT_POSTING_BOOKING_ID
            ),
            booking_date=date(2026, 7, 15),
            booking_type="REGULAR",
            voucher_no="GV-1",
            description=(
                "Zuführung gesetzliche Rücklage"
            ),
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
    )

    fixed_asset = ClientTransferFixedAsset(
        fixed_asset_id=FIXED_ASSET_ID,
        asset_code="BGA-001",
        description="Notebook",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="1200",
        depreciation_expense_account_number="1000",
        acquisition_date=date(2026, 2, 1),
        acquisition_cost="1200.00",
        depreciation_start_date=date(2026, 2, 1),
        useful_life_months=36,
        status="ACTIVE",
        movements=(
            ClientTransferFixedAssetMovement(
                movement_id=(
                    ACQUISITION_MOVEMENT_ID
                ),
                fiscal_year_end=date(
                    2026,
                    6,
                    30,
                ),
                movement_date=date(
                    2026,
                    2,
                    1,
                ),
                amount="1200.00",
                booking_line=(
                    ClientTransferBookingLineReference(
                        booking_id=(
                            ACQUISITION_BOOKING_ID
                        ),
                        position=0,
                    )
                ),
                movement_type="ACQUISITION",
            ),
        ),
        depreciations=(
            ClientTransferFixedAssetDepreciation(
                depreciation_id=DEPRECIATION_ID,
                fiscal_year_end=date(
                    2026,
                    6,
                    30,
                ),
                depreciation_date=date(
                    2026,
                    3,
                    31,
                ),
                amount="40.00",
                booking_line=(
                    ClientTransferBookingLineReference(
                        booking_id=(
                            DEPRECIATION_BOOKING_ID
                        ),
                        position=0,
                    )
                ),
                kind="LINEAR",
                source="CALCULATED",
                tax_adjustment=(
                    ClientTransferTaxDepreciationAdjustment(
                        depreciation_id=(
                            DEPRECIATION_ID
                        ),
                        tax_amount="50.00",
                    )
                ),
            ),
        ),
    )

    accounts = tuple(
        ClientTransferAccount(
            account_number=number,
            name=name,
            account_type=account_type,
            is_active=True,
            debit_position_code=(
                "HGB.266.AKTIVA.B.IV"
                if number == "1200"
                else None
            ),
        )
        for number, name, account_type in (
            ("0755", "Ausschüttungsverbindlichkeit", "LIABILITY"),
            ("0846", "Gesetzliche Rücklage", "EQUITY"),
            ("0855", "Andere Gewinnrücklagen", "EQUITY"),
            ("1000", "Kasse", "ASSET"),
            ("1200", "Bank", "ASSET"),
            ("1571", "Vorsteuer 7 %", "ASSET"),
            ("1576", "Vorsteuer 19 %", "ASSET"),
            ("1771", "Umsatzsteuer 7 %", "LIABILITY"),
            ("1776", "Umsatzsteuer 19 %", "LIABILITY"),
            ("2970", "Gewinn-/Verlustvortrag", "EQUITY"),
            ("4830", "Abschreibungen", "EXPENSE"),
            ("4900", "Anlagenabgang Gewinn", "REVENUE"),
            ("8020", "Gewinnkonto", "EQUITY"),
            ("8021", "Verlustkonto", "EQUITY"),
            ("8500", "Anlagenabgang Verlust", "EXPENSE"),
            ("9000", "Saldenvorträge", "EQUITY"),
        )
    )

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
            4,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Roundtrip Test UG",
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
            accounts=accounts,
            control_accounts=(
                ClientTransferControlAccounts(
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
                )
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
                    taxonomy_version=(
                        "test-version-2"
                    ),
                    account_number="1200",
                    concept_name="test.bank",
                ),
            ),
            shareholders=(
                ClientTransferShareholder(
                    shareholder_id=SHAREHOLDER_ID,
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
            fiscal_years=(
                ClientTransferFiscalYear(
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
                    status="CLOSED",
                    opening_source=None,
                    bookings=(
                        equity_booking,
                        acquisition_booking,
                        depreciation_booking,
                    ),
                ),
                ClientTransferFiscalYear(
                    start_date=date(
                        2026,
                        7,
                        1,
                    ),
                    end_date=date(
                        2027,
                        6,
                        30,
                    ),
                    status="OPEN",
                    opening_source=first_year,
                    bookings=(
                        profit_posting_booking,
                    ),
                ),
            ),
            fixed_assets=(
                fixed_asset,
            ),
            profit_appropriation_annual_data=(
                ClientTransferProfitAppropriationAnnualData(
                    fiscal_year=first_year,
                    statutory_reserve_addition=(
                        "100.00"
                    ),
                    other_revenue_reserves_addition=(
                        "0.00"
                    ),
                    statutory_reserve_release=(
                        "0.00"
                    ),
                    other_revenue_reserves_release=(
                        "0.00"
                    ),
                    distribution="0.00",
                    profit_loss_carryforward=(
                        "900.00"
                    ),
                ),
            ),
            profit_appropriation_postings=(
                ClientTransferProfitAppropriationPosting(
                    posting_id=PROFIT_POSTING_ID,
                    source_fiscal_year=first_year,
                    posting_date=date(
                        2026,
                        7,
                        15,
                    ),
                    amount="100.00",
                    booking_line=(
                        ClientTransferBookingLineReference(
                            booking_id=(
                                PROFIT_POSTING_BOOKING_ID
                            ),
                            position=0,
                        )
                    ),
                    posting_type=(
                        "STATUTORY_RESERVE_ADDITION"
                    ),
                ),
            ),
            equity_contributions=(
                ClientTransferEquityContribution(
                    booking_line=(
                        ClientTransferBookingLineReference(
                            booking_id=(
                                EQUITY_BOOKING_ID
                            ),
                            position=1,
                        )
                    ),
                ),
            ),
        ),
    )


def _import_and_export(
    *,
    engine,
    transfer: ClientTransfer,
) -> ClientTransfer:
    position_provider = (
        _build_position_provider()
    )

    with Session(engine) as session:
        repositories = _build_repositories(
            session
        )

        importer = _build_importer(
            repositories
        )

        importer.import_transfer(
            transfer=transfer,
            position_provider=position_provider,
        )

        exporter = _build_exporter(
            repositories
        )

        return exporter.export(
            company_id=transfer.client.company_id,
            position_provider=position_provider,
        )


def test_client_transfer_roundtrip_preserves_client_data(
) -> None:
    source_transfer = _build_rich_transfer()

    first_engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(
        first_engine
    )

    first_export = _import_and_export(
        engine=first_engine,
        transfer=source_transfer,
    )

    second_engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(
        second_engine
    )

    second_export = _import_and_export(
        engine=second_engine,
        transfer=first_export,
    )

    assert first_export.client == second_export.client
