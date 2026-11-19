from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_builder import FinancialStatementBuilder
from simpleob.accounting.financial_statement_context import (
    create_standard_financial_statement_context,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.accounting.trial_balance import TrialBalance
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Geschaeftspartner,
    Konto,
    Mandant,
    PersonenkontoZuordnung,
)
from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.booking_validator import BookingValidator
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.chart_of_accounts import ChartOfAccounts
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.errors import InvalidPersonAccountClassificationError
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.journal import Journal
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.services.posting_service import PostingService
from simpleob.services.reporting_service import ReportingService


@pytest.fixture
def database_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_fk(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    company = Company(company_id=uuid4(), name="Personenkonten UG")
    CompanyRepository(session).add(company)
    yield session, company
    session.close()
    engine.dispose()


def test_creates_both_roles_for_one_partner_and_loads_without_hgb_mapping(database_session):
    session, company = database_session
    repository = PersonAccountRepository(session)

    debtor = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Beispiel GmbH",
        account_number="10000",
    )
    creditor = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.KREDITOR,
        name="ignored when partner is reused",
        account_number="70000",
        partner_id=debtor.partner.partner_id,
    )

    assert debtor.partner.partner_id == creditor.partner.partner_id
    assert debtor.account.account_type is AccountType.ASSET
    assert creditor.account.account_type is AccountType.LIABILITY
    assert session.query(Geschaeftspartner).count() == 1
    assert session.query(PersonenkontoZuordnung).count() == 2
    assert session.query(Konto).filter_by(account_number="10000").one().debit_position_code is None
    assert session.query(Konto).filter_by(account_number="10000").one().credit_position_code is None

    context = create_standard_financial_statement_context()
    provider = HgbFinancialStatementPositionProvider(
        (context.assets, context.liabilities, context.income_statement)
    )
    loaded = ChartOfAccountsRepository(session).load_for_company(
        company_id=company.company_id,
        position_provider=provider,
    )
    assert loaded is not None
    chart, accounts = loaded
    assert chart.is_person_account("10000")
    assert chart.person_account_role("10000") is PersonAccountRole.DEBITOR
    assert chart.person_account_role("70000") is PersonAccountRole.KREDITOR
    assert not chart.account_mapping_rules
    assert next(account for account in accounts if account.number == "10000").person_account_role is PersonAccountRole.DEBITOR


def test_orphaned_five_digit_account_is_not_silently_mapped_or_ignored(
    database_session,
):
    session, company = database_session
    company_model = session.query(Mandant).filter_by(
        company_id=str(company.company_id)
    ).one()
    session.add(
        Konto(
            mandant_id=company_model.id,
            account_number="10000",
            name="Nicht zugeordnetes Konto",
            account_type="ASSET",
            is_active=True,
            debit_position_code="HGB.266.AKTIVA.B.II.1",
        )
    )
    session.commit()

    context = create_standard_financial_statement_context()
    provider = HgbFinancialStatementPositionProvider(
        (context.assets, context.liabilities, context.income_statement)
    )
    loaded = ChartOfAccountsRepository(session).load_for_company(
        company_id=company.company_id,
        position_provider=provider,
    )
    assert loaded is not None
    chart, _accounts = loaded
    assert not chart.is_person_account("10000")
    assert chart.person_account_role("10000") is None

    balance = AccountBalance(
        "10000",
        debit=Decimal("50.00"),
    )
    statement_builder = FinancialStatementBuilder(AccountMapper(chart))
    expected_error = "keine gültige Personenkontenzuordnung"
    with pytest.raises(InvalidPersonAccountClassificationError, match=expected_error):
        statement_builder.build((balance,))
    with pytest.raises(InvalidPersonAccountClassificationError, match=expected_error):
        AccountMapper(chart).position_for(balance)


def test_person_accounts_use_normal_booking_journal_ledger_and_reports(database_session):
    session, company = database_session
    repository = PersonAccountRepository(session)
    repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Kunde",
        account_number="10000",
    )
    repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.KREDITOR,
        name="Lieferant",
        account_number="70000",
    )
    context = create_standard_financial_statement_context()
    provider = HgbFinancialStatementPositionProvider(
        (context.assets, context.liabilities, context.income_statement)
    )
    _template, accounts = ChartOfAccountsRepository(session).load_for_company(
        company_id=company.company_id,
        position_provider=provider,
    )
    booking = Booking(
        booking_date=date(2026, 3, 1),
        voucher_no="PK-001",
        description="Personenkontenbuchung",
        lines=(
            BookingLine("10000", EntrySide.DEBIT, Decimal("125.00")),
            BookingLine("70000", EntrySide.CREDIT, Decimal("125.00")),
        ),
    )
    BookingValidator(ChartOfAccounts(accounts=accounts)).validate(booking)
    ledger = Ledger()
    journal = Journal()
    PostingService().post_booking(booking=booking, ledger=ledger, journal=journal)

    assert len(journal) == 1
    assert {balance.account_number for balance in ledger.balances()} == {
        "10000",
        "70000",
    }
    assert TrialBalance(ledger).is_turnover_balanced
    report = ReportingService().account_activity_report(
        journal=journal,
        account_number="10000",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    assert report.ending_balance == Decimal("125.00")
    assert len(report.lines) == 1


@pytest.mark.parametrize(
    ("role", "number"),
    [
        (PersonAccountRole.DEBITOR, "09999"),
        (PersonAccountRole.DEBITOR, "70000"),
        (PersonAccountRole.KREDITOR, "69999"),
        (PersonAccountRole.KREDITOR, "100000"),
        (PersonAccountRole.DEBITOR, "12a45"),
        (PersonAccountRole.DEBITOR, "١٠٠٠٠"),
        (PersonAccountRole.DEBITOR, "1000"),
    ],
)
def test_rejects_invalid_number_ranges_and_shapes(database_session, role, number):
    session, company = database_session
    with pytest.raises(ValueError):
        PersonAccountRepository(session).create(
            company_id=company.company_id,
            role=role,
            name="Ungültig",
            account_number=number,
        )
    assert session.query(Geschaeftspartner).count() == 0
    assert session.query(Konto).count() == 0


def test_number_suggestion_skips_existing_account_and_is_mandantenspezifisch(database_session):
    session, company = database_session
    other = Company(company_id=uuid4(), name="Anderer Mandant")
    CompanyRepository(session).add(other)
    session.add(
        Konto(
            mandant_id=session.query(Mandant).filter_by(
                company_id=str(company.company_id)
            ).one().id,
            account_number="10000",
            name="Sachkonto",
            account_type="ASSET",
            is_active=True,
        )
    )
    session.commit()
    repository = PersonAccountRepository(session)
    assert repository.suggest_account_number(
        company_id=company.company_id, role=PersonAccountRole.DEBITOR
    ) == "10001"
    assert repository.suggest_account_number(
        company_id=other.company_id, role=PersonAccountRole.DEBITOR
    ) == "10000"


def test_duplicate_number_and_partner_role_are_rejected(database_session):
    session, company = database_session
    repository = PersonAccountRepository(session)
    partner = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Kunde",
        account_number="69999",
    )
    with pytest.raises(ValueError, match="bereits ein Debitorenkonto"):
        repository.create(
            company_id=company.company_id,
            role=PersonAccountRole.DEBITOR,
            name="Kunde",
            account_number="69998",
            partner_id=partner.partner.partner_id,
        )
    with pytest.raises(Exception):
        repository.create(
            company_id=company.company_id,
            role=PersonAccountRole.DEBITOR,
            name="Andere Person",
            account_number="69999",
        )
    assert session.query(PersonenkontoZuordnung).count() == 1


def test_cross_mandant_foreign_keys_and_role_number_constraint(database_session):
    session, company = database_session
    other = Company(company_id=uuid4(), name="Zweiter Mandant")
    CompanyRepository(session).add(other)
    partner = BusinessPartner(company.company_id, "Kunde")
    BusinessPartnerRepository(session).add(partner)
    other_id = session.query(Mandant).filter_by(
        company_id=str(other.company_id)
    ).one().id
    session.add(Konto(
        mandant_id=other_id,
        account_number="10000",
        name="Konto",
        account_type="ASSET",
        is_active=True,
    ))
    session.commit()
    with pytest.raises(IntegrityError):
        session.add(PersonenkontoZuordnung(
            mandant_id=other_id,
            account_number="10000",
            partner_id=str(partner.partner_id),
            role="DEBITOR",
        ))
        session.commit()
    session.rollback()


def test_update_syncs_both_account_names_and_status_and_cannot_delete(database_session):
    session, company = database_session
    repository = PersonAccountRepository(session)
    debtor = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Vorher",
        account_number="10001",
    )
    creditor = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.KREDITOR,
        name="Vorher",
        account_number="70001",
        partner_id=debtor.partner.partner_id,
    )
    repository.update(
        company_id=company.company_id,
        account_number="10001",
        name="Nachher GmbH",
        is_active=False,
    )
    assert session.query(Konto).filter_by(account_number="10001").one().name == "Nachher GmbH"
    assert session.query(Konto).filter_by(account_number="70001").one().name == "Nachher GmbH"
    assert not session.query(Konto).filter_by(account_number="10001").one().is_active
    assert session.query(Konto).filter_by(account_number="70001").one().is_active
    assert repository.get(company_id=company.company_id, account_number="10001").partner.name == "Nachher GmbH"

    blocked = ChartOfAccountsRepository(session).delete_accounts(
        company_id=company.company_id,
        account_numbers=(debtor.account_number,),
    )
    assert "dauerhafte Personenkonto-Zuordnung" in blocked["10001"]
    repository.update(
        company_id=company.company_id,
        account_number="10001",
        name="Nachher GmbH",
        is_active=True,
    )
    assert repository.get(company_id=company.company_id, account_number="10001").account.is_active
    assert creditor.account_number == "70001"


def test_inactive_person_account_blocks_new_regular_booking_but_allows_opening_and_reversal(
    database_session,
):
    session, company = database_session
    fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
    CompanyRepository(session).add_fiscal_year(company.company_id, fiscal_year)
    repository = PersonAccountRepository(session)
    person_account = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Inaktiver Kunde",
        account_number="10003",
    )
    booking_repository = BookingRepository(session)
    original = Booking(
        booking_date=date(2026, 2, 1),
        description="Vor Deaktivierung",
        lines=(
            BookingLine("10003", EntrySide.DEBIT, Decimal("10.00")),
            BookingLine("9000", EntrySide.CREDIT, Decimal("10.00")),
        ),
    )
    booking_repository.add(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=original,
    )
    repository.update(
        company_id=company.company_id,
        account_number=person_account.account_number,
        name="Inaktiver Kunde",
        is_active=False,
    )

    inactive_booking = Booking(
        booking_date=date(2026, 3, 1),
        description="Nicht zulässig",
        lines=(
            BookingLine("10003", EntrySide.DEBIT, Decimal("5.00")),
            BookingLine("9000", EntrySide.CREDIT, Decimal("5.00")),
        ),
    )
    with pytest.raises(ValueError, match="inaktive Personenkonten"):
        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=inactive_booking,
        )

    opening = Booking(
        booking_date=fiscal_year.start_date,
        booking_type=BookingType.OPENING,
        description="Notwendiger Vortrag",
        lines=(
            BookingLine("10003", EntrySide.DEBIT, Decimal("10.00")),
            BookingLine("9000", EntrySide.CREDIT, Decimal("10.00")),
        ),
    )
    booking_repository.add(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=opening,
    )
    reversal = Booking(
        booking_date=date(2026, 4, 1),
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=original.booking_id,
        description="Storno trotz Deaktivierung",
        lines=(
            BookingLine("10003", EntrySide.CREDIT, Decimal("10.00")),
            BookingLine("9000", EntrySide.DEBIT, Decimal("10.00")),
        ),
    )
    booking_repository.add(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=reversal,
    )
    repository.update(
        company_id=company.company_id,
        account_number=person_account.account_number,
        name="Inaktiver Kunde",
        is_active=True,
    )
    reactivated_booking = Booking(
        booking_date=date(2026, 5, 1),
        description="Nach Reaktivierung",
        lines=(
            BookingLine("10003", EntrySide.DEBIT, Decimal("2.00")),
            BookingLine("9000", EntrySide.CREDIT, Decimal("2.00")),
        ),
    )
    booking_repository.add(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=reactivated_booking,
    )


def test_failed_creation_rolls_back_partner_and_account(database_session, monkeypatch):
    session, company = database_session

    def fail_add(*_args, **_kwargs):
        raise RuntimeError("simulierter Speicherfehler")

    monkeypatch.setattr(ChartOfAccountsRepository, "add_account", fail_add)
    with pytest.raises(RuntimeError, match="simulierter Speicherfehler"):
        PersonAccountRepository(session).create(
            company_id=company.company_id,
            role=PersonAccountRole.DEBITOR,
            name="Rollback",
            account_number="10002",
        )
    assert session.query(Geschaeftspartner).count() == 0
    assert session.query(Konto).count() == 0
    assert session.query(PersonenkontoZuordnung).count() == 0
