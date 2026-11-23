from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from simpleob.accounting.ledger import Ledger
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.journal import Journal
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.services.reporting_service import ReportingService

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))


def _person_accounts(company_id):
    partner = BusinessPartner(
        company_id=company_id,
        name="Muster GmbH",
        is_customer=True,
        is_supplier=True,
    )
    debtor = PersonAccount(
        Account(
            TemplateAccount("10000", partner.name, AccountType.ASSET),
            is_active=False,
            person_account_role=PersonAccountRole.DEBITOR,
        ),
        partner,
        PersonAccountRole.DEBITOR,
    )
    creditor = PersonAccount(
        Account(
            TemplateAccount("70000", partner.name, AccountType.LIABILITY),
            is_active=False,
            person_account_role=PersonAccountRole.KREDITOR,
        ),
        partner,
        PersonAccountRole.KREDITOR,
    )
    return debtor, creditor


def _booking(day, account, side, amount, *, booking_type=BookingType.REGULAR, text="Test"):
    other_side = EntrySide.CREDIT if side is EntrySide.DEBIT else EntrySide.DEBIT
    other_account = "9000" if account != "9000" else "9001"
    return Booking(
        booking_date=day,
        description=text,
        voucher_no=text,
        booking_type=booking_type,
        lines=(
            BookingLine(account, side, amount),
            BookingLine(other_account, other_side, amount),
        ),
    )


def test_person_account_summary_separates_roles_and_opposing_balances():
    company_id = uuid4()
    debtor, creditor = _person_accounts(company_id)
    journal = Journal()
    journal.add(
        _booking(
            date(2025, 12, 31),
            "10000",
            EntrySide.DEBIT,
            Decimal("999.00"),
            text="Außerhalb des Geschäftsjahres",
        )
    )
    journal.add(
        _booking(
            FY.start_date,
            "10000",
            EntrySide.DEBIT,
            Decimal("100.00"),
            booking_type=BookingType.OPENING,
            text="Saldovortrag Debitor",
        )
    )
    journal.add(
        _booking(
            FY.start_date,
            "70000",
            EntrySide.CREDIT,
            Decimal("50.00"),
            booking_type=BookingType.OPENING,
            text="Saldovortrag Kreditor",
        )
    )
    journal.add(_booking(date(2026, 2, 3), "10000", EntrySide.DEBIT, Decimal("20.10"), text="Rechnung"))
    journal.add(_booking(date(2026, 2, 3), "10000", EntrySide.CREDIT, Decimal("5.05"), text="Zahlung"))
    journal.add(_booking(date(2026, 2, 4), "70000", EntrySide.DEBIT, Decimal("10.00"), text="Korrektur"))
    journal.add(_booking(date(2026, 7, 1), "10000", EntrySide.DEBIT, Decimal("99.00"), text="Spätere Rechnung"))

    report = ReportingService().person_account_summary(
        ledger=Ledger(),
        journal=journal,
        fiscal_year=FY,
        company_id=company_id,
        person_accounts=(debtor, creditor),
        start_date=FY.start_date,
        end_date=date(2026, 6, 30),
        opening_balance_account_number="9000",
    )

    debtor_row, creditor_row = report.rows
    assert len(report.rows) == 2
    assert debtor_row.account_number == "10000"
    assert debtor_row.opening_balance == Decimal("100.00")
    assert debtor_row.debit_turnover == Decimal("20.10")
    assert debtor_row.credit_turnover == Decimal("5.05")
    assert debtor_row.ending_balance == Decimal("115.05")
    assert creditor_row.account_number == "70000"
    assert creditor_row.opening_balance == Decimal("-50.00")
    assert creditor_row.ending_balance == Decimal("-40.00")
    assert creditor_row.ending_debit_balance == Decimal("0.00")
    assert creditor_row.ending_credit_balance == Decimal("40.00")
    assert report.ending_debit_total == Decimal("115.05")
    assert report.ending_credit_total == Decimal("40.00")


def test_person_account_statement_uses_fiscal_opening_once_and_stable_order():
    company_id = uuid4()
    debtor, _creditor = _person_accounts(company_id)
    assert not debtor.account.is_active
    journal = Journal()
    journal.add(
        _booking(
            FY.start_date,
            "10000",
            EntrySide.DEBIT,
            Decimal("100.00"),
            booking_type=BookingType.OPENING,
            text="Saldovortrag",
        )
    )
    journal.add(_booking(date(2026, 2, 3), "10000", EntrySide.DEBIT, Decimal("20.00"), text="Erste Buchung"))
    journal.add(_booking(date(2026, 2, 3), "10000", EntrySide.CREDIT, Decimal("5.00"), text="Zweite Buchung"))
    journal.add(_booking(date(2026, 8, 1), "10000", EntrySide.CREDIT, Decimal("50.00"), text="Nach Stichtag"))

    report = ReportingService().person_account_statement(
        journal=journal,
        fiscal_year=FY,
        company_id=company_id,
        person_account=debtor,
        start_date=FY.start_date,
        end_date=date(2026, 6, 30),
        has_opening_source=True,
    )

    assert report.opening_balance == Decimal("0.00")
    assert report.carried_forward_balance == Decimal("100.00")
    assert [line.description for line in report.lines] == [
        "Saldovortrag",
        "Erste Buchung",
        "Zweite Buchung",
    ]
    assert [line.running_balance for line in report.lines] == [
        Decimal("100.00"),
        Decimal("120.00"),
        Decimal("115.00"),
    ]
    assert report.ending_balance == Decimal("115.00")


def test_person_account_summary_and_statement_include_unlinked_gl_postings():
    company_id = uuid4()
    _debtor, creditor = _person_accounts(company_id)
    fiscal_year = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
    journal = Journal()
    journal.add(
        _booking(
            date(2025, 6, 16),
            "70000",
            EntrySide.DEBIT,
            Decimal("210.78"),
            text="Direkte Hauptbuchbuchung 1",
        )
    )
    journal.add(
        _booking(
            date(2025, 6, 16),
            "70000",
            EntrySide.DEBIT,
            Decimal("292.75"),
            text="Direkte Hauptbuchbuchung 2",
        )
    )
    service = ReportingService()

    summary = service.person_account_summary(
        ledger=Ledger(),
        journal=journal,
        fiscal_year=fiscal_year,
        company_id=company_id,
        person_accounts=(creditor,),
        start_date=fiscal_year.start_date,
        end_date=fiscal_year.end_date,
        opening_balance_account_number="9000",
    )
    statement = service.person_account_statement(
        journal=journal,
        fiscal_year=fiscal_year,
        company_id=company_id,
        person_account=creditor,
        start_date=fiscal_year.start_date,
        end_date=fiscal_year.end_date,
        has_opening_source=False,
    )

    row = summary.rows[0]
    assert row.opening_balance == Decimal("0.00")
    assert row.debit_turnover == Decimal("503.53")
    assert row.credit_turnover == Decimal("0.00")
    assert row.ending_balance == Decimal("503.53")
    assert row.ending_debit_balance == Decimal("503.53")
    assert statement.opening_balance == Decimal("0.00")
    assert [line.debit for line in statement.lines] == [
        Decimal("210.78"),
        Decimal("292.75"),
    ]
    assert [line.running_balance for line in statement.lines] == [
        Decimal("210.78"),
        Decimal("503.53"),
    ]
    assert statement.ending_balance == row.ending_balance


def test_person_account_march_period_includes_february_as_opening_once():
    company_id = uuid4()
    debtor, creditor = _person_accounts(company_id)
    journal = Journal()
    journal.add(
        _booking(
            FY.start_date,
            "10000",
            EntrySide.DEBIT,
            Decimal("1000.00"),
            booking_type=BookingType.OPENING,
            text="Saldovortrag Debitor",
        )
    )
    journal.add(
        _booking(
            FY.start_date,
            "70000",
            EntrySide.CREDIT,
            Decimal("50.00"),
            booking_type=BookingType.OPENING,
            text="Saldovortrag Kreditor",
        )
    )
    journal.add(
        _booking(
            date(2026, 2, 15),
            "10000",
            EntrySide.CREDIT,
            Decimal("300.00"),
            text="Zahlungseingang",
        )
    )
    journal.add(
        _booking(
            date(2026, 2, 20),
            "70000",
            EntrySide.DEBIT,
            Decimal("75.00"),
            text="Lieferantengutschrift",
        )
    )
    journal.add(
        _booking(
            date(2026, 3, 10),
            "10000",
            EntrySide.DEBIT,
            Decimal("500.00"),
            text="Rechnung",
        )
    )
    journal.add(
        _booking(
            date(2026, 4, 1),
            "10000",
            EntrySide.CREDIT,
            Decimal("900.00"),
            text="Zahlung nach Zeitraum",
        )
    )

    report = ReportingService().person_account_summary(
        ledger=Ledger(),
        journal=journal,
        fiscal_year=FY,
        company_id=company_id,
        person_accounts=(debtor, creditor),
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        opening_balance_account_number="9000",
    )

    debtor_row, creditor_row = report.rows
    assert debtor_row.opening_balance == Decimal("700.00")
    assert debtor_row.debit_turnover == Decimal("500.00")
    assert debtor_row.credit_turnover == Decimal("0.00")
    assert debtor_row.ending_balance == Decimal("1200.00")
    assert creditor_row.opening_balance == Decimal("25.00")
    assert creditor_row.debit_turnover == Decimal("0.00")
    assert creditor_row.credit_turnover == Decimal("0.00")
    assert creditor_row.ending_debit_balance == Decimal("25.00")

    statement = ReportingService().person_account_statement(
        journal=journal,
        fiscal_year=FY,
        company_id=company_id,
        person_account=debtor,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        has_opening_source=True,
    )
    assert statement.opening_balance == Decimal("700.00")
    assert statement.carried_forward_balance == Decimal("1000.00")
    assert [line.description for line in statement.lines] == ["Rechnung"]
    assert statement.lines[0].running_balance == Decimal("1200.00")
    assert statement.ending_balance == Decimal("1200.00")


def test_person_account_reports_reject_other_mandates_and_out_of_year_dates():
    company_id = uuid4()
    debtor, _creditor = _person_accounts(company_id)
    journal = Journal()
    service = ReportingService()
    with pytest.raises(ValueError, match="anderen Mandanten"):
        service.person_account_summary(
            ledger=Ledger(),
            journal=journal,
            fiscal_year=FY,
            company_id=uuid4(),
            person_accounts=(debtor,),
            start_date=FY.start_date,
            end_date=FY.end_date,
            opening_balance_account_number="9000",
        )
    with pytest.raises(ValueError, match="innerhalb des Geschäftsjahres"):
        service.person_account_summary(
            ledger=Ledger(),
            journal=journal,
            fiscal_year=FY,
            company_id=company_id,
            person_accounts=(debtor,),
            start_date=date(2025, 12, 31),
            end_date=FY.end_date,
            opening_balance_account_number="9000",
        )
