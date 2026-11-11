from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.ledger import Ledger
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.services.posting_service import PostingService
from simpleob.services.vat_reconciliation_service import (
    VatReconciliationService,
)

FISCAL_YEAR = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT_ACCOUNTS = VatAccounts("1571", "1576", "1771", "1776")
ROLES = AccountingAccountRoles(
    cash_accounts=frozenset(),
    bank_accounts=frozenset(),
    general_rate_sales_accounts=frozenset(),
    vat_advance_payments=frozenset({"3820"}),
    vat_current_year=frozenset({"3840"}),
    vat_prior_year_receivables=frozenset({"1422"}),
    vat_prior_year_payables=frozenset({"3841"}),
)
ASSET_POSITION = FinancialStatementPosition(
    "HGB.266.AKTIVA.B.II.4",
    "Sonstige Vermögensgegenstände",
)
LIABILITY_POSITION = FinancialStatementPosition(
    "HGB.266.PASSIVA.C.8",
    "Sonstige Verbindlichkeiten",
)
CHART = ChartOfAccountsTemplate(
    name="VAT test chart",
    accounts=(
        TemplateAccount("1571", "Vorsteuer 7 %", AccountType.ASSET),
        TemplateAccount("1576", "Vorsteuer 19 %", AccountType.ASSET),
        TemplateAccount("1771", "Umsatzsteuer 7 %", AccountType.LIABILITY),
        TemplateAccount("1776", "Umsatzsteuer 19 %", AccountType.LIABILITY),
        TemplateAccount("3820", "Vorauszahlungen", AccountType.ASSET),
        TemplateAccount("3840", "Verrechnung", AccountType.LIABILITY),
    ),
    account_mapping_rules=(
        AccountMappingRule("1571", ASSET_POSITION, None),
        AccountMappingRule("1576", ASSET_POSITION, None),
        AccountMappingRule("1771", None, LIABILITY_POSITION),
        AccountMappingRule("1776", None, LIABILITY_POSITION),
        AccountMappingRule("3820", ASSET_POSITION, None),
        AccountMappingRule("3840", ASSET_POSITION, LIABILITY_POSITION),
    ),
)


def _build(ledger: Ledger, bookings: tuple[Booking, ...] = ()):
    return VatReconciliationService().build_proposal(
        bookings=bookings,
        ledger=ledger,
        fiscal_year=FISCAL_YEAR,
        vat_accounts=VAT_ACCOUNTS,
        account_roles=ROLES,
        chart_of_accounts=CHART,
    )


def _post(ledger: Ledger, debit: str, credit: str, amount: str) -> None:
    ledger.post(debit, credit, Decimal(amount))


def test_proposes_vat_payable_from_actual_general_ledger_balances() -> None:
    ledger = Ledger()
    _post(ledger, "1000", "1771", "10000.00")
    _post(ledger, "1571", "2000", "4000.00")
    _post(ledger, "3820", "1000", "5000.00")

    proposal = _build(ledger)

    assert proposal.resulting_clearing_balance == Decimal("-1000.00")
    assert len(proposal.bookings) == 3
    assert all(booking.is_balanced for booking in proposal.bookings)
    assert {
        line.amount
        for booking in proposal.bookings
        for line in booking.lines
        if line.account_number == "3840"
    } == {Decimal("10000.00"), Decimal("4000.00"), Decimal("5000.00")}
    for booking in proposal.bookings:
        PostingService().post_booking(booking=booking, ledger=ledger)
    assert ledger.get_account("3840").balance == Decimal("-1000.00")
    assert all(
        ledger.get_account(number).balance == Decimal("0.00")
        for number in ("1571", "1771", "3820")
    )


def test_proposes_vat_receivable() -> None:
    ledger = Ledger()
    _post(ledger, "1000", "1771", "4000.00")
    _post(ledger, "1571", "2000", "10000.00")
    _post(ledger, "3820", "1000", "5000.00")

    proposal = _build(ledger)

    assert proposal.resulting_clearing_balance == Decimal("11000.00")
    assert len(proposal.bookings) == 3


def test_proposes_zero_balance_without_losing_balanced_lines() -> None:
    ledger = Ledger()
    _post(ledger, "1000", "1771", "5000.00")
    _post(ledger, "1571", "2000", "2000.00")
    _post(ledger, "3820", "1000", "3000.00")

    proposal = _build(ledger)

    assert proposal.resulting_clearing_balance == Decimal("0.00")
    assert len(proposal.bookings) == 3
    assert all(booking.is_balanced for booking in proposal.bookings)


def test_handles_atypical_sides_and_existing_clearing_balance() -> None:
    ledger = Ledger()
    _post(ledger, "1771", "1000", "120.00")
    _post(ledger, "2000", "1571", "40.00")
    _post(ledger, "1000", "3820", "50.00")
    _post(ledger, "9000", "3840", "10.00")

    proposal = _build(ledger)

    assert proposal.existing_clearing_balance == Decimal("-10.00")
    assert proposal.resulting_clearing_balance == Decimal("20.00")
    assert len(proposal.bookings) == 3
    proposed_lines = {line for booking in proposal.bookings for line in booking.lines}
    assert BookingLine("1771", EntrySide.CREDIT, Decimal("120.00")) in proposed_lines
    assert BookingLine("1571", EntrySide.DEBIT, Decimal("40.00")) in proposed_lines
    assert BookingLine("3820", EntrySide.DEBIT, Decimal("50.00")) in proposed_lines


@pytest.mark.parametrize("account_number", ("1571", "3820", "3840"))
def test_rejects_unresolved_opening_balance_on_tax_account(
    account_number: str,
) -> None:
    ledger = Ledger()
    opening = Booking(
        booking_id=uuid4(),
        booking_date=FISCAL_YEAR.start_date,
        booking_type=BookingType.OPENING,
        lines=(
            BookingLine(account_number, EntrySide.DEBIT, Decimal("60.00")),
            BookingLine("9000", EntrySide.CREDIT, Decimal("60.00")),
        ),
    )
    PostingService().post_booking(booking=opening, ledger=ledger)

    with pytest.raises(ValueError, match=f"{account_number}: 60.00 €"):
        _build(ledger, (opening,))


def test_only_remaining_balances_are_proposed_after_prior_partial_clearing() -> None:
    ledger = Ledger()
    _post(ledger, "1000", "1771", "10000.00")
    previous_clear = Booking(
        booking_date=date(2026, 11, 30),
        booking_type=BookingType.REGULAR,
        lines=(
            BookingLine("1771", EntrySide.DEBIT, Decimal("3000.00")),
            BookingLine("3840", EntrySide.CREDIT, Decimal("3000.00")),
        ),
    )
    PostingService().post_booking(
        booking=previous_clear,
        ledger=ledger,
    )

    proposal = _build(ledger, (previous_clear,))

    assert proposal.existing_clearing_balance == Decimal("-3000.00")
    assert proposal.resulting_clearing_balance == Decimal("-10000.00")
    assert len(proposal.bookings) == 1
    assert proposal.bookings[0].debit_total == Decimal("7000.00")
    assert proposal.bookings[0].credit_total == Decimal("7000.00")


def test_same_bookings_produce_no_duplicate_after_proposal_is_posted() -> None:
    ledger = Ledger()
    _post(ledger, "1000", "1771", "10000.00")
    _post(ledger, "1571", "2000", "4000.00")
    _post(ledger, "3820", "1000", "5000.00")
    service = VatReconciliationService()
    initial_bookings: tuple[Booking, ...] = ()
    proposal = service.build_proposal(
        bookings=initial_bookings,
        ledger=ledger,
        fiscal_year=FISCAL_YEAR,
        vat_accounts=VAT_ACCOUNTS,
        account_roles=ROLES,
        chart_of_accounts=CHART,
    )
    assert proposal.bookings
    for booking in proposal.bookings:
        PostingService().post_booking(booking=booking, ledger=ledger)

    second = service.build_proposal(
        bookings=proposal.bookings,
        ledger=ledger,
        fiscal_year=FISCAL_YEAR,
        vat_accounts=VAT_ACCOUNTS,
        account_roles=ROLES,
        chart_of_accounts=CHART,
    )

    assert not second.bookings
    assert second.resulting_clearing_balance == Decimal("-1000.00")
