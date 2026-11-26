from datetime import date
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from simpleob.core.context import ApplicationContext
from simpleob.database.bank_transaction_booking_repository import (
    BankTransactionBookingRepository,
)
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.models import BankTransactionBooking, Buchung
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.bank_booking_proposal import (
    CounterBookingLineProposal,
    build_booking_proposals,
)
from simpleob.domain.company import Company
from simpleob.domain.errors import DuplicateBankTransactionError, UnknownAccountError
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.template_account import TemplateAccount
from simpleob.importers.qonto_csv_importer import QontoCsvImporter
from simpleob.services.bank_booking_import_service import BankBookingImportService
from simpleob.services.fiscal_year_workspace import FiscalYearWorkspace


class ImportDatabase:
    def __init__(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.companies = CompanyRepository(self.session)
        self.accounts = ChartOfAccountsRepository(self.session)
        self.booking_repository = BookingRepository(self.session)
        self.transaction_repository = BankTransactionBookingRepository(self.session)
        self.company = self.add_company("Importtest A")
        self.fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
        self.companies.add_fiscal_year(self.company.company_id, self.fiscal_year)
        self._add_chart(self.company)

    def add_company(self, name: str) -> Company:
        company = Company(uuid4(), name)
        self.companies.add(company)
        return company

    def _add_chart(self, company: Company) -> None:
        for number, name, account_type in (
            ("1200", "Bank", AccountType.ASSET),
            ("4930", "Bürobedarf", AccountType.EXPENSE),
            ("1576", "Vorsteuer", AccountType.ASSET),
        ):
            self.accounts.add_account(
                company_id=company.company_id,
                account=Account(TemplateAccount(number, name, account_type)),
                mapping_rule=None,
            )
        self.accounts.save_account_roles(
            company_id=company.company_id,
            account_roles=AccountingAccountRoles(
                cash_accounts=frozenset(),
                bank_accounts=frozenset({"1200"}),
                general_rate_sales_accounts=frozenset(),
            ),
        )

    def service(self) -> BankBookingImportService:
        return BankBookingImportService(
            booking_repository=self.booking_repository,
            transaction_booking_repository=self.transaction_repository,
        )

    def dispose(self) -> None:
        self.session.close()
        self.engine.dispose()


@pytest.fixture
def db() -> ImportDatabase:
    database = ImportDatabase()
    try:
        yield database
    finally:
        database.dispose()


def _proposal(
    transaction_id: str = "TX-1",
    amount: str = "100,00",
    *,
    contra_account: str = "4930",
    contra_amount: Decimal | None = None,
):
    csv_text = (
        "Transaction ID;Status;Settlement date (local);Counterparty name;"
        "Reference;Total amount (incl. VAT);Currency\n"
        f"{transaction_id};completed;16.11.2026;Lieferant;Überweisung;{amount};EUR"
    )
    transaction = QontoCsvImporter().load_file(StringIO(csv_text))[0]
    proposal = build_booking_proposals((transaction,))[0]
    proposal.bank_account_number = "1200"
    proposal.counter_lines = (
        CounterBookingLineProposal(
            contra_account,
            contra_amount if contra_amount is not None else abs(transaction.amount),
        ),
    )
    return proposal


def _confirm(db: ImportDatabase, proposal, *, company=None, confirmed=True):
    return db.service().confirm_and_post(
        proposal,
        company=company or db.company,
        fiscal_year=db.fiscal_year,
        bank_account_numbers=frozenset({"1200"}),
        confirmed=confirmed,
    )


def test_confirms_and_persists_booking_with_external_reference(db: ImportDatabase) -> None:
    proposal = _proposal()

    booking = _confirm(db, proposal)

    assert db.session.query(Buchung).count() == 1
    assert len(db.booking_repository.list_for_fiscal_year(
        company_id=db.company.company_id,
        fiscal_year=db.fiscal_year,
    )) == 1
    assert db.transaction_repository.booking_id_for(
        company_id=db.company.company_id,
        import_source=proposal.transaction.import_source,
        external_transaction_id="TX-1",
    ) == booking.booking_id


def test_rejects_second_confirmation_of_same_transaction(db: ImportDatabase) -> None:
    _confirm(db, _proposal())

    with pytest.raises(DuplicateBankTransactionError):
        _confirm(db, _proposal())

    assert db.session.query(Buchung).count() == 1
    assert db.session.query(BankTransactionBooking).count() == 1


def test_database_constraint_rejects_duplicate_external_id(db: ImportDatabase) -> None:
    first_booking = _confirm(db, _proposal("TX-1"))
    second_booking = _confirm(db, _proposal("TX-2"))
    source = _proposal("TX-1").transaction.import_source

    with pytest.raises(IntegrityError):
        db.transaction_repository.add(
            company_id=db.company.company_id,
            import_source=source,
            external_transaction_id="TX-1",
            booking_id=second_booking.booking_id,
        )
    db.session.rollback()

    assert db.transaction_repository.booking_id_for(
        company_id=db.company.company_id,
        import_source=source,
        external_transaction_id="TX-1",
    ) == first_booking.booking_id
    assert db.session.query(BankTransactionBooking).count() == 2
    assert db.session.query(Buchung).count() == 2


def test_same_external_id_is_allowed_for_another_company(db: ImportDatabase) -> None:
    _confirm(db, _proposal("SAME-ID"))
    second_company = db.add_company("Importtest B")
    db.companies.add_fiscal_year(second_company.company_id, db.fiscal_year)
    db._add_chart(second_company)

    second_booking = _confirm(db, _proposal("SAME-ID"), company=second_company)

    assert db.session.query(Buchung).count() == 2
    assert db.transaction_repository.booking_id_for(
        company_id=second_company.company_id,
        import_source=_proposal("SAME-ID").transaction.import_source,
        external_transaction_id="SAME-ID",
    ) == second_booking.booking_id


def test_invalid_booking_leaves_no_booking_or_import_reference(db: ImportDatabase) -> None:
    proposal = _proposal(contra_account="9999")

    with pytest.raises(UnknownAccountError):
        _confirm(db, proposal)

    assert db.session.query(Buchung).count() == 0
    assert db.session.query(BankTransactionBooking).count() == 0


def test_failed_import_reference_insert_rolls_back_booking(db: ImportDatabase) -> None:
    class BrokenReferenceRepository(BankTransactionBookingRepository):
        def add(self, **kwargs) -> None:
            self._session.add(
                BankTransactionBooking(
                    mandant_id=1,
                    import_source=kwargs["import_source"].value,
                    external_transaction_id=kwargs["external_transaction_id"],
                    booking_id=str(uuid4()),
                )
            )

    service = BankBookingImportService(
        booking_repository=db.booking_repository,
        transaction_booking_repository=BrokenReferenceRepository(db.session),
    )

    with pytest.raises(IntegrityError):
        service.confirm_and_post(
            _proposal(),
            company=db.company,
            fiscal_year=db.fiscal_year,
            bank_account_numbers=frozenset({"1200"}),
            confirmed=True,
        )

    assert db.session.query(Buchung).count() == 0
    assert db.session.query(BankTransactionBooking).count() == 0


def test_persists_multi_line_booking_proposal(db: ImportDatabase) -> None:
    proposal = _proposal()
    proposal.counter_lines = (
        CounterBookingLineProposal("4930", Decimal("80.00")),
        CounterBookingLineProposal("1576", Decimal("20.00")),
    )

    booking = _confirm(db, proposal)

    assert len(booking.lines) == 3
    loaded = db.booking_repository.get(booking.booking_id)
    assert loaded is not None
    assert len(loaded.lines) == 3


def test_workspace_reloads_after_successful_confirmation(db: ImportDatabase) -> None:
    workspace = object.__new__(FiscalYearWorkspace)
    workspace._context = ApplicationContext(db.company, db.fiscal_year)
    workspace._booking_repository = db.booking_repository
    workspace._bank_transaction_booking_repository = db.transaction_repository
    workspace._chart_of_accounts_repository = db.accounts
    refreshes: list[bool] = []
    workspace.reload = lambda: refreshes.append(True)

    workspace.post_bank_booking_proposal(_proposal(), confirmed=True)

    assert refreshes == [True]


@pytest.mark.parametrize("transaction_already_active", (False, True))
def test_workspace_cleans_only_its_own_transaction_on_early_rejection(
    db: ImportDatabase,
    transaction_already_active: bool,
) -> None:
    if transaction_already_active:
        db.session.execute(text("SELECT 1"))
    workspace = object.__new__(FiscalYearWorkspace)
    workspace._context = ApplicationContext(db.company, db.fiscal_year)
    workspace._booking_repository = db.booking_repository
    workspace._bank_transaction_booking_repository = db.transaction_repository
    workspace._chart_of_accounts_repository = db.accounts

    with pytest.raises(ValueError, match="nicht ausdrücklich bestätigt"):
        workspace.post_bank_booking_proposal(_proposal(), confirmed=False)

    assert db.booking_repository.has_active_transaction is transaction_already_active
    assert db.session.query(Buchung).count() == 0
    assert db.session.query(BankTransactionBooking).count() == 0


def test_requires_explicit_confirmation(db: ImportDatabase) -> None:
    with pytest.raises(ValueError, match="nicht ausdrücklich bestätigt"):
        _confirm(db, _proposal(), confirmed=False)
    assert db.session.query(Buchung).count() == 0
    assert db.session.query(BankTransactionBooking).count() == 0
