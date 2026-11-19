"""Roundtrip-Tests für den portablen Mandantentransfer."""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.client_transfer.archive import (
    read_client_transfer_archive,
    write_client_transfer_archive,
)
from simpleob.client_transfer.exporter import (
    ClientTransferExporter,
)
from simpleob.client_transfer.importer import (
    ClientTransferImporter,
)
from simpleob.client_transfer.model import (
    CLIENT_TRANSFER_FORMAT_NAME,
    CLIENT_TRANSFER_FORMAT_VERSION,
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferBookingLineReference,
    ClientTransferBusinessPartner,
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferEquityContribution,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferFormat,
    ClientTransferKrAnnualTurnover,
    ClientTransferKrSettings,
    ClientTransferMasterData,
    ClientTransferPersonAccount,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
    ClientTransferShareholder,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
)
from simpleob.client_transfer.serialization import (
    client_transfer_from_dict,
    client_transfer_to_dict,
)
from simpleob.database.booking_repository import (
    BookingRepository,
)
from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from simpleob.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from simpleob.database.models import (
    Geschaeftspartner,
    Konto,
    Mandant,
    PersonenkontoZuordnung,
)
from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from simpleob.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from simpleob.database.shareholder_repository import (
    ShareholderRepository,
)
from simpleob.database.tax_depreciation_adjustment_repository import (
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
        "person_account_repository": PersonAccountRepository(session),
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
        person_account_repository=(
            repositories["person_account_repository"]
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
        person_account_repository=(
            repositories["person_account_repository"]
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
            kr_settings=ClientTransferKrSettings(
                activity_start_date=date(2019, 8, 1),
                waiver_declared=True,
                waiver_date=date(2025, 4, 1),
                external_turnovers=(
                    ClientTransferKrAnnualTurnover(2024, "2500.10"),
                    ClientTransferKrAnnualTurnover(2025, "3000.20"),
                ),
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


def test_client_transfer_archive_roundtrip_preserves_client_data(
    tmp_path: Path,
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

    archive_path = (
        tmp_path / "roundtrip.simpleob"
    )

    write_client_transfer_archive(
        archive_path,
        first_export,
    )

    archived_transfer = (
        read_client_transfer_archive(
            archive_path
        )
    )

    assert archived_transfer == first_export

    second_engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(
        second_engine
    )

    second_export = _import_and_export(
        engine=second_engine,
        transfer=archived_transfer,
    )

    assert (
        first_export.client
        == second_export.client
    )


@pytest.mark.parametrize(
    ("roles", "statuses"),
    [
        (("DEBITOR",), (False,)),
        (("KREDITOR",), (True,)),
        (("DEBITOR", "KREDITOR"), (False, True)),
    ],
)
def test_person_account_transfer_roundtrip_preserves_partner_links_and_status(
    roles, statuses
) -> None:
    partner_id = UUID("22222222-2222-2222-2222-222222222222")
    source = _build_rich_transfer()
    added_accounts = []
    person_accounts = []
    for role, is_active in zip(roles, statuses):
        number = "10000" if role == "DEBITOR" else "70000"
        added_accounts.append(
            ClientTransferAccount(
                account_number=number,
                name="Transferpartner GmbH",
                account_type="ASSET" if role == "DEBITOR" else "LIABILITY",
                is_active=is_active,
            )
        )
        person_accounts.append(
            ClientTransferPersonAccount(
                account_number=number,
                partner_id=partner_id,
                role=role,
            )
        )
    transferred = replace(
        source,
        client=replace(
            source.client,
            accounts=source.client.accounts + tuple(added_accounts),
            business_partners=(
                ClientTransferBusinessPartner(
                    partner_id=partner_id,
                    name="Transferpartner GmbH",
                    is_customer="DEBITOR" in roles,
                    is_supplier="KREDITOR" in roles,
                    is_active=False,
                ),
            ),
            person_accounts=tuple(person_accounts),
        ),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    exported = _import_and_export(engine=engine, transfer=transferred)

    assert exported.format.version == 2
    assert exported.client.person_accounts == tuple(person_accounts)
    assert exported.client.business_partners == transferred.client.business_partners
    assert next(
        account for account in exported.client.accounts
        if account.account_number == "1200"
    ).debit_position_code == "HGB.266.AKTIVA.B.IV"
    exported_accounts_by_number = {
        account.account_number: account for account in exported.client.accounts
    }
    for source_account in added_accounts:
        exported_account = exported_accounts_by_number[source_account.account_number]
        assert exported_account.account_number == source_account.account_number
        assert exported_account.name == source_account.name
        assert exported_account.is_active == source_account.is_active
        assert exported_account.debit_position_code is None
        assert exported_account.credit_position_code is None
    engine.dispose()


def test_accounting_transfer_roundtrip_preserves_person_accounts_vat_and_reversals(
    tmp_path: Path,
) -> None:
    partner_id = UUID("22222222-2222-2222-2222-222222222222")
    source = _build_rich_transfer()
    accounts = source.client.accounts + (
        ClientTransferAccount(
            account_number="10000",
            name="Transferpartner GmbH",
            account_type="ASSET",
            is_active=True,
        ),
        ClientTransferAccount(
            account_number="70000",
            name="Transferpartner GmbH",
            account_type="LIABILITY",
            is_active=True,
        ),
    )
    invoice_booking = ClientTransferBooking(
        booking_id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
        booking_date=date(2026, 8, 10),
        booking_type="REGULAR",
        description="Manuelle Ausgangsrechnungsbuchung",
        lines=(
            ClientTransferBookingLine(0, "10000", "DEBIT", "119.00"),
            ClientTransferBookingLine(1, "4900", "CREDIT", "100.00"),
            ClientTransferBookingLine(2, "1776", "CREDIT", "19.00"),
        ),
    )
    payable_booking = ClientTransferBooking(
        booking_id=UUID("bbbbbbbb-1111-1111-1111-111111111111"),
        booking_date=date(2026, 8, 11),
        booking_type="REGULAR",
        description="Manuelle Eingangsrechnungsbuchung",
        lines=(
            ClientTransferBookingLine(0, "4830", "DEBIT", "100.00"),
            ClientTransferBookingLine(1, "1576", "DEBIT", "19.00"),
            ClientTransferBookingLine(2, "70000", "CREDIT", "119.00"),
        ),
    )
    original_booking_id = UUID("cccccccc-1111-1111-1111-111111111111")
    original_booking = ClientTransferBooking(
        booking_id=original_booking_id,
        booking_date=date(2026, 8, 12),
        booking_type="REGULAR",
        description="Zu stornierende Buchung",
        lines=(
            ClientTransferBookingLine(0, "1200", "DEBIT", "5.00"),
            ClientTransferBookingLine(1, "4900", "CREDIT", "5.00"),
        ),
    )
    reversal_booking = ClientTransferBooking(
        booking_id=UUID("dddddddd-1111-1111-1111-111111111111"),
        booking_date=date(2026, 8, 13),
        booking_type="REVERSAL",
        reversal_of_booking_id=original_booking_id,
        description="Storno der Buchung",
        lines=(
            ClientTransferBookingLine(0, "1200", "CREDIT", "5.00"),
            ClientTransferBookingLine(1, "4900", "DEBIT", "5.00"),
        ),
    )
    fiscal_years = list(source.client.fiscal_years)
    open_year = fiscal_years[1]
    fiscal_years[1] = replace(
        open_year,
        bookings=(
            *open_year.bookings,
            invoice_booking,
            payable_booking,
            original_booking,
            reversal_booking,
        ),
    )
    transfer = replace(
        source,
        client=replace(
            source.client,
            accounts=accounts,
            business_partners=(
                ClientTransferBusinessPartner(
                    partner_id=partner_id,
                    name="Transferpartner GmbH",
                    is_customer=True,
                    is_supplier=True,
                    is_active=True,
                ),
            ),
            person_accounts=(
                ClientTransferPersonAccount(
                    account_number="10000",
                    partner_id=partner_id,
                    role="DEBITOR",
                ),
                ClientTransferPersonAccount(
                    account_number="70000",
                    partner_id=partner_id,
                    role="KREDITOR",
                ),
            ),
            fiscal_years=tuple(fiscal_years),
        ),
    )

    source_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(source_engine)
    source_export = _import_and_export(engine=source_engine, transfer=transfer)
    archive_path = tmp_path / "personenkonten-rundlauf.simpleob"
    write_client_transfer_archive(archive_path, source_export)
    archived_transfer = read_client_transfer_archive(archive_path)

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(target_engine)
    target_export = _import_and_export(
        engine=target_engine,
        transfer=archived_transfer,
    )

    assert target_export.client == source_export.client
    assert target_export.client.business_partners == (
        ClientTransferBusinessPartner(
            partner_id=partner_id,
            name="Transferpartner GmbH",
            is_customer=True,
            is_supplier=True,
            is_active=True,
        ),
    )
    assert target_export.client.person_accounts == (
        ClientTransferPersonAccount("10000", partner_id, "DEBITOR"),
        ClientTransferPersonAccount("70000", partner_id, "KREDITOR"),
    )
    imported_bookings = {
        booking.booking_id: booking
        for fiscal_year in target_export.client.fiscal_years
        for booking in fiscal_year.bookings
    }
    assert imported_bookings[invoice_booking.booking_id].lines == invoice_booking.lines
    assert imported_bookings[payable_booking.booking_id].lines == payable_booking.lines
    assert imported_bookings[reversal_booking.booking_id].reversal_of_booking_id == (
        original_booking_id
    )
    assert target_export.client.account_roles == source_export.client.account_roles

    def balances_by_account(client):
        balances = {}
        for fiscal_year in client.fiscal_years:
            for booking in fiscal_year.bookings:
                for line in booking.lines:
                    amount = Decimal(line.amount)
                    balances[line.account_number] = balances.get(
                        line.account_number, Decimal("0.00")
                    ) + (amount if line.side == "DEBIT" else -amount)
        return balances

    assert balances_by_account(target_export.client) == balances_by_account(
        source_export.client
    )
    target_balances = balances_by_account(target_export.client)
    assert target_balances["10000"] == Decimal("119.00")
    assert target_balances["70000"] == Decimal("-119.00")
    assert target_balances["1576"] == Decimal("19.00")
    assert target_balances["1776"] == Decimal("-19.00")
    source_engine.dispose()
    target_engine.dispose()


@pytest.mark.parametrize("format_version", (1, 2))
def test_legacy_open_item_roles_are_ignored_during_transfer_import(
    format_version: int,
) -> None:
    source = _build_rich_transfer()
    legacy_role_accounts = (
        ClientTransferAccount("1400", "Kundenforderungen", "ASSET", True),
        ClientTransferAccount(
            "1600", "Lieferantenverbindlichkeiten", "LIABILITY", True
        ),
        ClientTransferAccount("1610", "Kundenguthaben", "LIABILITY", True),
        ClientTransferAccount("1410", "Lieferantenguthaben", "ASSET", True),
    )
    transfer = replace(
        source,
        format=ClientTransferFormat(version=format_version),
        client=replace(
            source.client,
            accounts=source.client.accounts + legacy_role_accounts,
        ),
    )
    legacy_data = client_transfer_to_dict(transfer)
    legacy_data["client"]["account_roles"].update(
        {
            "customer_receivables": ["1400"],
            "supplier_payables": ["1600"],
            "customer_credit_balances": ["1610"],
            "supplier_credit_balances": ["1410"],
        }
    )
    legacy_transfer = client_transfer_from_dict(legacy_data)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    imported = _import_and_export(engine=engine, transfer=legacy_transfer)

    assert imported.client.kr_settings == transfer.client.kr_settings
    assert imported.client.account_roles == transfer.client.account_roles
    assert {
        account.account_number for account in imported.client.accounts
    } >= {"1400", "1600", "1610", "1410"}
    with Session(engine) as session:
        roles = ChartOfAccountsRepository(session).load_account_roles(
            company_id=transfer.client.company_id
        )
    assert roles.customer_receivables == frozenset()
    assert roles.supplier_payables == frozenset()
    assert roles.customer_credit_balances == frozenset()
    assert roles.supplier_credit_balances == frozenset()
    engine.dispose()


def test_person_account_import_failure_rolls_back_partner_account_and_link(
    monkeypatch,
) -> None:
    partner_id = UUID("22222222-2222-2222-2222-222222222222")
    source = _build_rich_transfer()
    transfer = replace(
        source,
        client=replace(
            source.client,
            accounts=source.client.accounts
            + (
                ClientTransferAccount(
                    account_number="10000",
                    name="Rollback GmbH",
                    account_type="ASSET",
                    is_active=True,
                ),
            ),
            business_partners=(
                ClientTransferBusinessPartner(
                    partner_id=partner_id,
                    name="Rollback GmbH",
                    is_customer=True,
                    is_supplier=False,
                    is_active=True,
                ),
            ),
            person_accounts=(
                ClientTransferPersonAccount(
                    account_number="10000",
                    partner_id=partner_id,
                    role="DEBITOR",
                ),
            ),
        ),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repositories = _build_repositories(session)
        person_repository = repositories["person_account_repository"]
        original_import = person_repository.import_transfer_records

        def fail_after_person_records(**kwargs):
            original_import(**kwargs)
            raise RuntimeError("simulierter später Importfehler")

        monkeypatch.setattr(
            person_repository, "import_transfer_records", fail_after_person_records
        )
        importer = _build_importer(repositories)
        with pytest.raises(RuntimeError, match="simulierter später Importfehler"):
            importer.import_transfer(
                transfer=transfer,
                position_provider=_build_position_provider(),
            )
        assert session.query(Mandant).count() == 0
        assert session.query(Konto).count() == 0
        assert session.query(Geschaeftspartner).count() == 0
        assert session.query(PersonenkontoZuordnung).count() == 0
    engine.dispose()


def test_import_of_legacy_transfer_defaults_kr_settings() -> None:
    source_transfer = _build_rich_transfer()
    legacy_transfer = replace(
        source_transfer,
        format=ClientTransferFormat(version=1),
        client=replace(
            source_transfer.client,
            kr_settings=None,
            business_partners=(),
            person_accounts=(),
        ),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    exported = _import_and_export(engine=engine, transfer=legacy_transfer)

    assert exported.client.kr_settings is not None
    assert exported.client.kr_settings.activity_start_date is None
    assert exported.client.kr_settings.waiver_declared is False
    assert exported.client.kr_settings.external_turnovers == ()
