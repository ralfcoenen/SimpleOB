"""Tests für das unveränderliche Modell zur Rücknahme von Guthabenrückerstattungen."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from simpleob.database.database import Base
from simpleob.database.models import (
    Buchung,
    Geschaeftspartner,
    GuthabenOP,
    GuthabenOPRueckerstattung,
    GuthabenOPRueckerstattungsruecknahme,
    Gutschrift,
    Mandant,
    Wirtschaftsjahr,
)


@pytest.fixture
def refund_context():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    mandate = Mandant(company_id=str(uuid4()), name="Rücknahmetest")
    year = Wirtschaftsjahr(
        mandant=mandate,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="OPEN",
    )
    session.add_all((mandate, year))
    session.flush()
    partner = Geschaeftspartner(
        partner_id=str(uuid4()),
        mandant_id=mandate.id,
        name="Testkunde",
        is_customer=True,
        is_supplier=False,
        is_active=True,
    )
    original_booking = Buchung(
        booking_id=str(uuid4()),
        wirtschaftsjahr=year,
        booking_date=date(2026, 2, 1),
        booking_type="REGULAR",
    )
    refund_booking = Buchung(
        booking_id=str(uuid4()),
        wirtschaftsjahr=year,
        booking_date=date(2026, 3, 1),
        booking_type="REGULAR",
    )
    reversal_booking = Buchung(
        booking_id=str(uuid4()),
        wirtschaftsjahr=year,
        booking_date=date(2026, 3, 2),
        booking_type="REVERSAL",
        reversal_of_booking_id=refund_booking.booking_id,
    )
    alternate_reversal_booking = Buchung(
        booking_id=str(uuid4()),
        wirtschaftsjahr=year,
        booking_date=date(2026, 3, 3),
        booking_type="REVERSAL",
        reversal_of_booking_id=refund_booking.booking_id,
    )
    session.add_all(
        (
            partner,
            original_booking,
            refund_booking,
            reversal_booking,
            alternate_reversal_booking,
        )
    )
    session.flush()
    credit_note = Gutschrift(
        credit_note_id=str(uuid4()),
        mandant_id=mandate.id,
        partner_id=partner.partner_id,
        credit_note_kind="CUSTOMER",
        note_number="GS-TEST-1",
        note_date=date(2026, 2, 1),
        booking_id=original_booking.booking_id,
    )
    open_item = GuthabenOP(
        open_item_id=str(uuid4()),
        credit_note_id=credit_note.credit_note_id,
        amount=Decimal("100.00"),
    )
    refund = GuthabenOPRueckerstattung(
        refund_id=str(uuid4()),
        mandant_id=mandate.id,
        partner_id=partner.partner_id,
        open_item_id=open_item.open_item_id,
        direction="CUSTOMER",
        amount=Decimal("25.00"),
        refund_date=date(2026, 3, 1),
        booking_id=refund_booking.booking_id,
        recorded_at=datetime(2026, 3, 1, 12, tzinfo=timezone.utc),
    )
    session.add(credit_note)
    session.flush()
    session.add(open_item)
    session.flush()
    session.add(refund)
    session.commit()
    context = {
        "session": session,
        "refund": refund,
        "reversal_booking": reversal_booking,
        "alternate_reversal_booking": alternate_reversal_booking,
    }
    yield context
    session.close()
    engine.dispose()


def _reversal_record(context, *, reversal_id=None, refund_id=None, booking_id=None, reason="Irrtümliche Erfassung"):
    return GuthabenOPRueckerstattungsruecknahme(
        reversal_id=str(reversal_id or uuid4()),
        refund_id=str(refund_id or context["refund"].refund_id),
        reversal_booking_id=str(
            booking_id or context["reversal_booking"].booking_id
        ),
        recorded_at=datetime(2026, 3, 2, 12, tzinfo=timezone.utc),
        reason=reason,
    )


def test_saves_refund_reversal_and_resolves_source_relationships(refund_context) -> None:
    session = refund_context["session"]
    reversal = _reversal_record(refund_context)
    session.add(reversal)
    session.commit()

    loaded = (
        session.query(GuthabenOPRueckerstattungsruecknahme)
        .filter_by(reversal_id=reversal.reversal_id)
        .one()
    )
    assert loaded.refund.refund_id == refund_context["refund"].refund_id
    assert loaded.refund.open_item_id == refund_context["refund"].open_item_id
    assert loaded.refund.amount == Decimal("25.00")
    assert loaded.reversal_booking.booking_date == date(2026, 3, 2)
    assert loaded.reversal_booking.wirtschaftsjahr.start_date == date(2026, 1, 1)


def test_refund_can_only_be_reversed_once(refund_context) -> None:
    session = refund_context["session"]
    session.add(_reversal_record(refund_context))
    session.commit()

    session.add(
        _reversal_record(
            refund_context,
            booking_id=refund_context["alternate_reversal_booking"].booking_id,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


@pytest.mark.parametrize(
    "invalid_record",
    [
        lambda context: _reversal_record(context, reason=None),
        lambda context: _reversal_record(context, reason="   "),
        lambda context: _reversal_record(context, refund_id="missing-refund"),
        lambda context: _reversal_record(context, booking_id="missing-booking"),
    ],
    ids=("required-reason", "nonempty-reason", "refund-foreign-key", "booking-foreign-key"),
)
def test_required_reason_and_foreign_keys_are_enforced(refund_context, invalid_record) -> None:
    session = refund_context["session"]
    session.add(invalid_record(refund_context))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
