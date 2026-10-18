"""Tests für den Workflow der Ergebnisverwendungsbuchungen."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from unittest.mock import Mock

from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.booking_repository import (
    BookingRepository,
)
from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from simpleob.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from simpleob.services.profit_appropriation_booking_service import (
    ProfitAppropriationBookingService,
)
from simpleob.services.profit_appropriation_posting_workflow import (
    ProfitAppropriationPostingWorkflow,
)


def _source_fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _target_fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )


def _proposal() -> ProfitAppropriationPostingProposal:
    return ProfitAppropriationPostingProposal(
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
        booking_date=date(2027, 3, 15),
        amount=Decimal("5000.00"),
        debit_account_number="2970",
        credit_account_number="0755",
    )



def _validation_dependencies(
    proposal: ProfitAppropriationPostingProposal,
) -> tuple[Mock, Mock, Mock]:
    """Stellt gültige Grundlagen für Workflowtests bereit."""

    chart_repository = Mock()
    chart_repository.load_control_accounts.return_value = Mock()

    annual_repository = Mock()
    annual_repository.get_for_fiscal_year.return_value = (
        ProfitAppropriationAnnualData(
            statutory_reserve_addition=Decimal("0.00"),
            other_revenue_reserves_addition=Decimal("0.00"),
            statutory_reserve_release=Decimal("0.00"),
            other_revenue_reserves_release=Decimal("0.00"),
            distribution=Decimal("5000.00"),
            profit_loss_carryforward=Decimal("0.00"),
        )
    )

    posting_service = Mock()
    posting_service.build_proposals.return_value = (proposal,)

    return (
        chart_repository,
        annual_repository,
        posting_service,
    )



def test_confirms_profit_appropriation_posting_atomically() -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()
    proposal = _proposal()

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
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

        (
            chart_repository,
            annual_repository,
            posting_service,
        ) = _validation_dependencies(_proposal())

        workflow = ProfitAppropriationPostingWorkflow(
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_repository=posting_repository,
            booking_service=(
                ProfitAppropriationBookingService()
            ),
            chart_of_accounts_repository=chart_repository,
            annual_data_repository=annual_repository,
            posting_service=posting_service,
        )

        posting = workflow.confirm(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            proposal=proposal,
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

        postings = (
            posting_repository.list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

    assert len(bookings) == 1
    assert postings == (posting,)

    booking = bookings[0]

    assert posting.booking_id == booking.booking_id
    assert posting.source_fiscal_year_end == date(
        2026,
        12,
        31,
    )
    assert posting.posting_date == date(
        2027,
        3,
        15,
    )
    assert posting.amount == Decimal("5000.00")
    assert (
        posting.posting_type
        is ProfitAppropriationPostingType.DISTRIBUTION
    )

    assert booking.booking_date == date(
        2027,
        3,
        15,
    )
    assert booking.lines[0].account_number == "2970"
    assert booking.lines[1].account_number == "0755"


def test_rejects_target_without_source_as_opening_source() -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
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

        (
            chart_repository,
            annual_repository,
            posting_service,
        ) = _validation_dependencies(_proposal())

        workflow = ProfitAppropriationPostingWorkflow(
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_repository=posting_repository,
            booking_service=(
                ProfitAppropriationBookingService()
            ),
            chart_of_accounts_repository=chart_repository,
            annual_data_repository=annual_repository,
            posting_service=posting_service,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Zielgeschäftsjahr wurde nicht aus dem "
                "Quellgeschäftsjahr eröffnet"
            ),
        ):
            workflow.confirm(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                proposal=_proposal(),
            )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

    assert bookings == ()


def test_rolls_back_booking_when_posting_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
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

        (
            chart_repository,
            annual_repository,
            posting_service,
        ) = _validation_dependencies(_proposal())

        workflow = ProfitAppropriationPostingWorkflow(
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_repository=posting_repository,
            booking_service=(
                ProfitAppropriationBookingService()
            ),
            chart_of_accounts_repository=chart_repository,
            annual_data_repository=annual_repository,
            posting_service=posting_service,
        )

        def fail_add(*args, **kwargs) -> None:
            raise RuntimeError(
                "Testfehler beim Speichern des Nachweises"
            )

        monkeypatch.setattr(
            posting_repository,
            "add",
            fail_add,
        )

        with pytest.raises(
            RuntimeError,
            match="Testfehler beim Speichern des Nachweises",
        ):
            workflow.confirm(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                proposal=_proposal(),
            )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

    assert bookings == ()



def test_rejects_outdated_profit_appropriation_amount() -> None:
    """Ein veralteter Betrag darf nicht gebucht werden."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()
    original_proposal = _proposal()

    with Session() as session:
        company_repository = CompanyRepository(session)
        booking_repository = BookingRepository(session)
        posting_repository = (
            ProfitAppropriationPostingRepository(session)
        )

        company_repository.add(company)
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

        (
            chart_repository,
            annual_repository,
            posting_service,
        ) = _validation_dependencies(original_proposal)

        # Die inzwischen gültigen Jahresdaten ergeben
        # nur noch eine Ausschüttung von 4.000 EUR.
        annual_repository.get_for_fiscal_year.return_value = (
            ProfitAppropriationAnnualData(
                statutory_reserve_addition=Decimal("0.00"),
                other_revenue_reserves_addition=Decimal("0.00"),
                statutory_reserve_release=Decimal("0.00"),
                other_revenue_reserves_release=Decimal("0.00"),
                distribution=Decimal("4000.00"),
                profit_loss_carryforward=Decimal("0.00"),
            )
        )

        current_proposal = (
            ProfitAppropriationPostingProposal(
                posting_type=original_proposal.posting_type,
                booking_date=original_proposal.booking_date,
                amount=Decimal("4000.00"),
                debit_account_number=(
                    original_proposal.debit_account_number
                ),
                credit_account_number=(
                    original_proposal.credit_account_number
                ),
            )
        )
        posting_service.build_proposals.return_value = (
            current_proposal,
        )

        workflow = ProfitAppropriationPostingWorkflow(
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_repository=posting_repository,
            booking_service=(
                ProfitAppropriationBookingService()
            ),
            chart_of_accounts_repository=chart_repository,
            annual_data_repository=annual_repository,
            posting_service=posting_service,
        )

        with pytest.raises(
            ValueError,
            match="zwischenzeitlich veraltet",
        ):
            workflow.confirm(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                proposal=original_proposal,
            )

        bookings = booking_repository.list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
        )
        postings = (
            posting_repository.list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

    assert bookings == ()
    assert postings == ()


def test_rejects_outdated_profit_appropriation_account() -> None:
    """Eine veraltete Kontenzuordnung darf nicht gebucht werden."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()
    original_proposal = _proposal()

    with Session() as session:
        company_repository = CompanyRepository(session)
        booking_repository = BookingRepository(session)
        posting_repository = (
            ProfitAppropriationPostingRepository(session)
        )

        company_repository.add(company)
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

        (
            chart_repository,
            annual_repository,
            posting_service,
        ) = _validation_dependencies(original_proposal)

        # Betrag bleibt gleich; das Gegenkonto
        # wurde zwischenzeitlich geändert.
        current_proposal = (
            ProfitAppropriationPostingProposal(
                posting_type=original_proposal.posting_type,
                booking_date=original_proposal.booking_date,
                amount=original_proposal.amount,
                debit_account_number=(
                    original_proposal.debit_account_number
                ),
                credit_account_number="0756",
            )
        )
        posting_service.build_proposals.return_value = (
            current_proposal,
        )

        workflow = ProfitAppropriationPostingWorkflow(
            session=session,
            company_repository=company_repository,
            booking_repository=booking_repository,
            posting_repository=posting_repository,
            booking_service=(
                ProfitAppropriationBookingService()
            ),
            chart_of_accounts_repository=chart_repository,
            annual_data_repository=annual_repository,
            posting_service=posting_service,
        )

        with pytest.raises(
            ValueError,
            match="zwischenzeitlich veraltet",
        ):
            workflow.confirm(
                company_id=company.company_id,
                source_fiscal_year=source_fiscal_year,
                target_fiscal_year=target_fiscal_year,
                proposal=original_proposal,
            )

        bookings = booking_repository.list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
        )
        postings = (
            posting_repository.list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

    assert bookings == ()
    assert postings == ()
