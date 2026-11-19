"""Tests für die Überleitung in ein neues Geschäftsjahr."""

from datetime import date
from decimal import Decimal

import pytest

from simpleob.accounting.financial_statement_position import FinancialStatementPosition
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.journal import Journal
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from simpleob.services.posting_service import PostingService


def test_creates_opening_bookings_for_balance_sheet_accounts() -> None:
    """Nur Bestandskonten werden in das neue Geschäftsjahr vorgetragen."""

    ledger = Ledger()
    journal = Journal()
    posting_service = PostingService()

    bookings = (
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung",
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("25000.00"),
                ),
                BookingLine(
                    account_number="9000",
                    side=EntrySide.CREDIT,
                    amount=Decimal("25000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 8),
            description="Büromaterial",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("500.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("500.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 9),
            description="Umsatzerlös",
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("2000.00"),
                ),
                BookingLine(
                    account_number="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("2000.00"),
                ),
            ),
        ),
    )

    for booking in bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        "1200": AccountType.ASSET,
        "1600": AccountType.LIABILITY,
        "1800": AccountType.EQUITY,
        "2970": AccountType.EQUITY,
        "4980": AccountType.EXPENSE,
        "8020": AccountType.EQUITY,
        "8021": AccountType.EQUITY,
        "8400": AccountType.REVENUE,
        "9000": AccountType.EQUITY,
    }

    service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )

    transfer_bookings = service.create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    assert len(transfer_bookings) == 1

    booking = transfer_bookings[0]

    assert booking.booking_date == date(2027, 1, 1)
    assert booking.description == "Saldovortrag Konto 1200"

    assert booking.lines == (
        BookingLine(
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("26500.00"),
        ),
        BookingLine(
            account_number="9000",
            side=EntrySide.CREDIT,
            amount=Decimal("26500.00"),
        ),
    )

    transferred_accounts = {
        line.account_number
        for transfer_booking in transfer_bookings
        for line in transfer_booking.lines
    }

    assert "4980" not in transferred_accounts
    assert "8400" not in transferred_accounts


def test_creates_opening_bookings_for_credit_balances() -> None:
    """Passiv- und Eigenkapitalkonten werden im Haben vorgetragen."""

    ledger = Ledger()
    journal = Journal()
    posting_service = PostingService()

    bookings = (
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Verbindlichkeiten",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("8000.00"),
                ),
                BookingLine(
                    account_number="1600",
                    side=EntrySide.CREDIT,
                    amount=Decimal("8000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Eigenkapital",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("17000.00"),
                ),
                BookingLine(
                    account_number="1800",
                    side=EntrySide.CREDIT,
                    amount=Decimal("17000.00"),
                ),
            ),
        ),
    )

    for booking in bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        "1600": AccountType.LIABILITY,
        "1800": AccountType.EQUITY,
        "2970": AccountType.EQUITY,
        "8020": AccountType.EQUITY,
        "8021": AccountType.EQUITY,
        "9000": AccountType.EQUITY,
    }

    service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )

    transfer_bookings = service.create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    assert len(transfer_bookings) == 2

    assert transfer_bookings[0].lines == (
        BookingLine(
            account_number="9000",
            side=EntrySide.DEBIT,
            amount=Decimal("8000.00"),
        ),
        BookingLine(
            account_number="1600",
            side=EntrySide.CREDIT,
            amount=Decimal("8000.00"),
        ),
    )

    assert transfer_bookings[1].lines == (
        BookingLine(
            account_number="9000",
            side=EntrySide.DEBIT,
            amount=Decimal("17000.00"),
        ),
        BookingLine(
            account_number="1800",
            side=EntrySide.CREDIT,
            amount=Decimal("17000.00"),
        ),
    )


def test_transfers_all_person_account_balance_directions_to_same_accounts():
    ledger = Ledger()
    for account_number, side, amount in (
        ("10000", EntrySide.DEBIT, Decimal("100.01")),
        ("10001", EntrySide.CREDIT, Decimal("20.02")),
        ("70000", EntrySide.CREDIT, Decimal("30.03")),
        ("70001", EntrySide.DEBIT, Decimal("10.04")),
    ):
        if side is EntrySide.DEBIT:
            ledger.post(account_number, "9999", amount)
        else:
            ledger.post("9999", account_number, amount)

    account_types = {
        "10000": AccountType.ASSET,
        "10001": AccountType.ASSET,
        "70000": AccountType.LIABILITY,
        "70001": AccountType.LIABILITY,
        "9999": AccountType.EQUITY,
        "9000": AccountType.EQUITY,
    }
    service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )

    transfers = service.create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    person_transfers = {
        booking.description.removeprefix("Saldovortrag Konto "): booking
        for booking in transfers
        if booking.description.startswith("Saldovortrag Konto ")
        and booking.description.removeprefix("Saldovortrag Konto ")
        in {"10000", "10001", "70000", "70001"}
    }
    assert set(person_transfers) == {"10000", "10001", "70000", "70001"}
    for account_number, side, amount in (
        ("10000", EntrySide.DEBIT, Decimal("100.01")),
        ("10001", EntrySide.CREDIT, Decimal("20.02")),
        ("70000", EntrySide.CREDIT, Decimal("30.03")),
        ("70001", EntrySide.DEBIT, Decimal("10.04")),
    ):
        person_line = next(
            line
            for line in person_transfers[account_number].lines
            if line.account_number == account_number
        )
        assert person_line.side is side
        assert person_line.amount == amount

    chart = ChartOfAccountsTemplate(
        "Personenkonten",
        tuple(
            TemplateAccount(
                number,
                number,
                account_types[number],
            )
            for number in ("10000", "10001", "70000", "70001")
        ),
        person_account_roles=(
            ("10000", PersonAccountRole.DEBITOR),
            ("10001", PersonAccountRole.DEBITOR),
            ("70000", PersonAccountRole.KREDITOR),
            ("70001", PersonAccountRole.KREDITOR),
        ),
    )
    mapper = AccountMapper(chart)
    next_year_ledger = Ledger()
    next_year_posting_service = PostingService()
    for transfer_booking in transfers:
        next_year_posting_service.post_booking(
            booking=transfer_booking,
            ledger=next_year_ledger,
        )
    expected_positions = {
        "10000": "HGB.266.AKTIVA.B.II.1",
        "10001": "HGB.266.PASSIVA.C.4",
        "70000": "HGB.266.PASSIVA.C.4",
        "70001": "HGB.266.AKTIVA.B.II.1",
    }
    for account_number, expected_code in expected_positions.items():
        position, amount = mapper.map_balance(
            next_year_ledger.get_account(account_number)
        )
        assert position.code == expected_code
        assert amount > Decimal("0.00")


def _vat_transfer_configuration(*, missing_mapping: str | None = None):
    accounts = (
        TemplateAccount("3820", "Umsatzsteuer-Vorauszahlungen", AccountType.ASSET),
        TemplateAccount("3840", "Umsatzsteuer laufendes Jahr", AccountType.LIABILITY),
        TemplateAccount("1422", "Umsatzsteuerforderungen Vorjahr", AccountType.ASSET),
        TemplateAccount("3841", "Umsatzsteuerverbindlichkeiten Vorjahr", AccountType.LIABILITY),
    )
    positions = {
        "asset": FinancialStatementPosition(
            "HGB.266.AKTIVA.B.II.4", "Sonstige Vermögensgegenstände"
        ),
        "liability": FinancialStatementPosition(
            "HGB.266.PASSIVA.C.8", "Sonstige Verbindlichkeiten"
        ),
    }
    mapping_sides = {
        "3820": ("asset", None),
        "3840": ("asset", "liability"),
        "1422": ("asset", None),
        "3841": (None, "liability"),
    }
    rules = tuple(
        AccountMappingRule(
            account_number=number,
            debit_position=positions[debit] if debit else None,
            credit_position=positions[credit] if credit else None,
        )
        for number, (debit, credit) in mapping_sides.items()
        if number != missing_mapping
    )
    chart = ChartOfAccountsTemplate(
        name="VAT test chart",
        accounts=accounts,
        account_mapping_rules=rules,
    )
    roles = AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset(),
        general_rate_sales_accounts=frozenset(),
        vat_advance_payments=frozenset({"3820"}),
        vat_current_year=frozenset({"3840"}),
        vat_prior_year_receivables=frozenset({"1422"}),
        vat_prior_year_payables=frozenset({"3841"}),
    )
    account_types = {
        account.account_number: account.account_type
        for account in accounts
    }
    account_types["9000"] = AccountType.EQUITY
    return chart, roles, account_types


def _vat_transfer_service() -> FiscalYearTransferService:
    return FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )


def _vat_openings(ledger: Ledger, *, missing_mapping: str | None = None):
    chart, roles, account_types = _vat_transfer_configuration(
        missing_mapping=missing_mapping
    )
    return _vat_transfer_service().create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
        account_roles=roles,
        chart_of_accounts=chart,
    )


def test_carries_debit_balance_of_vat_current_year_to_prior_year_receivable():
    ledger = Ledger()
    ledger.post("3840", "9000", Decimal("125.50"))

    (booking,) = _vat_openings(ledger)

    assert booking.lines == (
        BookingLine("1422", EntrySide.DEBIT, Decimal("125.50")),
        BookingLine("9000", EntrySide.CREDIT, Decimal("125.50")),
    )


def test_carries_credit_balance_of_vat_current_year_to_prior_year_payable():
    ledger = Ledger()
    ledger.post("9000", "3840", Decimal("75.25"))

    (booking,) = _vat_openings(ledger)

    assert booking.lines == (
        BookingLine("9000", EntrySide.DEBIT, Decimal("75.25")),
        BookingLine("3841", EntrySide.CREDIT, Decimal("75.25")),
    )


def test_does_not_create_vat_opening_for_zero_balance():
    ledger = Ledger()
    ledger.post("3840", "9000", Decimal("100.00"))
    ledger.post("9000", "3840", Decimal("100.00"))

    assert _vat_openings(ledger) == ()


def test_carries_existing_prior_year_vat_balances_on_the_same_accounts():
    ledger = Ledger()
    ledger.post("1422", "9000", Decimal("40.00"))
    ledger.post("9000", "3841", Decimal("80.00"))

    bookings = _vat_openings(ledger)

    target_lines = {
        line.account_number: line
        for booking in bookings
        for line in booking.lines
        if line.account_number in {"1422", "3841"}
    }
    assert target_lines == {
        "1422": BookingLine("1422", EntrySide.DEBIT, Decimal("40.00")),
        "3841": BookingLine("3841", EntrySide.CREDIT, Decimal("80.00")),
    }
    assert all(
        sum(line.amount for line in booking.lines if line.side is EntrySide.DEBIT)
        == sum(line.amount for line in booking.lines if line.side is EntrySide.CREDIT)
        for booking in bookings
    )


def test_rejects_missing_vat_opening_account_or_hgb_mapping():
    ledger = Ledger()
    ledger.post("3840", "9000", Decimal("10.00"))
    chart, roles, account_types = _vat_transfer_configuration()
    account_types.pop("1422")
    with pytest.raises(ValueError, match="1422.*nicht vorhanden"):
        _vat_transfer_service().create_opening_bookings(
            ledger=ledger,
            account_types=account_types,
            opening_date=date(2027, 1, 1),
            account_roles=roles,
            chart_of_accounts=chart,
        )

    with pytest.raises(ValueError, match="3841.*HGB-Haben-Zuordnung"):
        _vat_openings(ledger, missing_mapping="3841")
