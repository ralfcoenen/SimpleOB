"""Integrationstests für die persistente Geschäftsjahreseröffnung."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.ledger import Ledger
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.journal import Journal
from openbilanz.services.fiscal_year_opening_workflow import (
    FiscalYearOpeningWorkflow,
)
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.services.posting_service import PostingService


def test_opens_fiscal_year_and_persists_opening_source() -> None:
    """Eröffnungsbuchungen und Herkunft werden gemeinsam gespeichert."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    closing_balance_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Abschlusssalden",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("25000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    posting_service.post_booking(
        booking=closing_balance_booking,
        journal=journal_2026,
        ledger=ledger_2026,
    )

    account_types = {
        "1200": AccountType.ASSET,
        "1800": AccountType.EQUITY,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            source_ledger=ledger_2026,
            account_types=account_types,
        )

    assert len(opening_bookings) == 2

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        managed_fiscal_years = (
            company_repository.get_managed_fiscal_years(
                company.company_id
            )
        )

        persisted_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

    assert len(persisted_bookings) == 2

    assert {
        booking.description
        for booking in persisted_bookings
    } == {
        "Saldovortrag Konto 1200",
        "Saldovortrag Konto 1800",
    }

    assert managed_fiscal_years[0].status is FiscalYearStatus.CLOSED

    assert (
        managed_fiscal_years[1].fiscal_year
        == target_fiscal_year
    )

    assert (
        managed_fiscal_years[1].opening_source
        == source_fiscal_year
    )
    
def test_rejects_opening_from_open_fiscal_year() -> None:
    """Ein offenes Geschäftsjahr darf nicht als Eröffnungsquelle dienen."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match="Quellgeschäftsjahr ist nicht abgeschlossen.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )

def test_rolls_back_opening_when_opening_source_fails() -> None:
    """Bei einem Fehler wird die Geschäftsjahreseröffnung zurückgerollt."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    closing_balance_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Abschlusssalden",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("25000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    posting_service.post_booking(
        booking=closing_balance_booking,
        journal=journal_2026,
        ledger=ledger_2026,
    )

    account_types = {
        "1200": AccountType.ASSET,
        "1800": AccountType.EQUITY,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        def failing_set_opening_source(
            *args: object,
            **kwargs: object,
        ) -> None:
            raise RuntimeError(
                "Simulierter Fehler"
            )

        company_repository.set_opening_source = (  # type: ignore[method-assign]
            failing_set_opening_source
        )

        with pytest.raises(
            RuntimeError,
            match="Simulierter Fehler",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        persisted_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

        managed_fiscal_years = (
            company_repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert persisted_bookings == ()

    assert (
        managed_fiscal_years[1].opening_source
        is None
    )

def test_rolls_back_session_when_opening_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Der Workflow rollt seine Transaktion bei einem Fehler zurück."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    closing_balance_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Abschlusssalden",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("25000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    posting_service.post_booking(
        booking=closing_balance_booking,
        journal=journal_2026,
        ledger=ledger_2026,
    )

    account_types = {
        "1200": AccountType.ASSET,
        "1800": AccountType.EQUITY,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        rollback_called = False
        original_rollback = session.rollback

        def recording_rollback() -> None:
            nonlocal rollback_called
            rollback_called = True
            original_rollback()

        monkeypatch.setattr(
            session,
            "rollback",
            recording_rollback,
        )

        def failing_set_opening_source(
            *args: object,
            **kwargs: object,
        ) -> None:
            raise RuntimeError(
                "Simulierter Fehler"
            )

        monkeypatch.setattr(
            company_repository,
            "set_opening_source",
            failing_set_opening_source,
        )

        with pytest.raises(
            RuntimeError,
            match="Simulierter Fehler",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )

        assert rollback_called

        persisted_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

        assert persisted_bookings == ()

def test_rejects_opening_when_target_fiscal_year_is_missing() -> None:
    """Ein nicht vorhandenes Zielgeschäftsjahr kann nicht eröffnet werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    missing_target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr wurde nicht gefunden.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=missing_target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )


def test_rejects_opening_into_closed_target_fiscal_year() -> None:
    """Ein abgeschlossenes Zielgeschäftsjahr kann nicht eröffnet werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr ist bereits abgeschlossen.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )

def test_rejects_opening_into_same_fiscal_year() -> None:
    """Ein Geschäftsjahr kann nicht aus sich selbst eröffnet werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    ledger = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Quell- und Zielgeschäftsjahr "
                "dürfen nicht identisch sein."
            ),
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=fiscal_year,
                target_fiscal_year=fiscal_year,
                source_ledger=ledger,
                account_types=account_types,
            )

def test_rejects_opening_when_target_already_has_opening_source() -> None:
    """Ein bereits eröffnetes Zielgeschäftsjahr kann nicht erneut eröffnet werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.set_opening_source(
            company.company_id,
            target_fiscal_year,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr wurde bereits eröffnet.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2026,
                account_types=account_types,
            )

def test_rejects_non_consecutive_fiscal_years() -> None:
    """Die Eröffnungsquelle muss dem Zieljahr unmittelbar vorausgehen."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2025 = Ledger()

    account_types = {
        "1200": AccountType.ASSET,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Quellgeschäftsjahr geht dem Zielgeschäftsjahr "
                "nicht unmittelbar voraus."
            ),
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                source_ledger=ledger_2025,
                account_types=account_types,
            )

def test_opens_fiscal_year_after_short_fiscal_year() -> None:
    """Ein Rumpfgeschäftsjahr kann korrekt in das Folgejahr überleiten."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    closing_balance_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Abschlusssalden",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("25000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    posting_service.post_booking(
        booking=closing_balance_booking,
        journal=journal_2026,
        ledger=ledger_2026,
    )

    account_types = {
        "1200": AccountType.ASSET,
        "1800": AccountType.EQUITY,
    }

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            source_ledger=ledger_2026,
            account_types=account_types,
        )

    assert len(opening_bookings) == 2

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        managed_fiscal_years = (
            company_repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert (
        managed_fiscal_years[1].opening_source
        == source_fiscal_year
    )

