"""Integrationstests für die persistente Geschäftsjahreseröffnung."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.accounting.ledger import Ledger
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.journal import Journal
from simpleob.services.fiscal_year_opening_workflow import (
    FiscalYearOpeningWorkflow,
)
from simpleob.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from simpleob.services.posting_service import PostingService


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

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=source_fiscal_year,
            booking=closing_balance_booking,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service=FiscalYearTransferService(
            opening_balance_account_number="9000",
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        with pytest.raises(
            ValueError,
            match="Quellgeschäftsjahr ist nicht abgeschlossen.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr wurde nicht gefunden.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=missing_target_fiscal_year,
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr ist bereits abgeschlossen.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService()
        )

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr wurde bereits eröffnet.",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
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

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=source_fiscal_year,
            booking=closing_balance_booking,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
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


def test_reconstructs_source_ledger_from_persisted_bookings() -> None:
    """Die Eröffnung verwendet die persistenten Buchungen des Quelljahres."""

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

    source_booking = Booking(
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

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=source_fiscal_year,
            booking=source_booking,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        transfer_service = FiscalYearTransferService(
            opening_balance_account_number="9000",
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            account_types=account_types,
        )

    assert len(opening_bookings) == 2

    assert {
        booking.description
        for booking in opening_bookings
    } == {
        "Saldovortrag Konto 1200",
        "Saldovortrag Konto 1800",
    }

def test_opens_fiscal_year_without_opening_bookings() -> None:
    """Ein leeres Quelljahr kann ohne Eröffnungsbuchungen eröffnet werden."""

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
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=transfer_service,
            posting_service=PostingService(),
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            account_types={},
        )

    assert opening_bookings == ()

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

    target_managed_fiscal_year = next(
        managed
        for managed in managed_fiscal_years
        if managed.fiscal_year == target_fiscal_year
    )

    assert persisted_bookings == ()

    assert (
        target_managed_fiscal_year.opening_source
        == source_fiscal_year
    )

def test_rolls_back_when_source_ledger_reconstruction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fehler bei der Ledger-Rekonstruktion lösen einen Rollback aus."""

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

    source_booking = Booking(
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

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=source_fiscal_year,
            booking=source_booking,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        posting_service = PostingService()

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=FiscalYearTransferService(
                opening_balance_account_number="9000",
                profit_account_number="8020",
                loss_account_number="8021",
                profit_loss_carryforward_account_number="2970",
            ),
            posting_service=posting_service,
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

        def failing_post_booking(
            *args: object,
            **kwargs: object,
        ) -> None:
            raise RuntimeError(
                "Simulierter Rekonstruktionsfehler"
            )

        monkeypatch.setattr(
            posting_service,
            "post_booking",
            failing_post_booking,
        )

        with pytest.raises(
            RuntimeError,
            match="Simulierter Rekonstruktionsfehler",
        ):
            workflow.open(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                account_types=account_types,
            )

        assert rollback_called

def test_reconstructs_source_ledger_only_from_company_bookings() -> None:
    """Buchungen anderer Mandanten beeinflussen die Eröffnung nicht."""

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

    other_company = Company(
        company_id=uuid4(),
        name="Andere UG",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    company_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Eigene Abschlusssalden",
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

    other_company_booking = Booking(
        booking_date=date(2026, 12, 31),
        description="Fremde Abschlusssalden",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("99000.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("99000.00"),
            ),
        ),
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

        company_repository.add(
            other_company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        company_repository.add_fiscal_year(
            other_company.company_id,
            source_fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=source_fiscal_year,
            booking=company_booking,
        )

        booking_repository.add(
            company_id=other_company.company_id,
            fiscal_year=source_fiscal_year,
            booking=other_company_booking,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        workflow = FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            transfer_service=FiscalYearTransferService(
                opening_balance_account_number="9000",
                profit_account_number="8020",
                loss_account_number="8021",
                profit_loss_carryforward_account_number="2970",
            ),
            posting_service=PostingService(),
        )

        opening_bookings = workflow.open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            account_types=account_types,
        )

    assert len(opening_bookings) == 2

    amounts_by_account = {
        line.account_number: line.amount
        for booking in opening_bookings
        for line in booking.lines
        if line.account_number != "9000"
    }

    assert amounts_by_account == {
        "1200": Decimal("25000.00"),
        "1800": Decimal("25000.00"),
    }
