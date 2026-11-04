"""Lesende Abfragen für die informative KR-Grenzüberwachung."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session, aliased

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Buchungszeile,
    ForderungsOP,
    GuthabenOP,
    GuthabenOPRueckerstattung,
    GuthabenOPRueckerstattungsruecknahme,
    Gutschrift,
    Konto,
    Mandant,
    RechnungsOPStorno,
    RechnungsOPZahlungsereignis,
    Wirtschaftsjahr,
    Zahlung,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking_type import BookingType
from simpleob.domain.kr_monitoring import KrCalendarYearTotals
from simpleob.domain.money import ZERO


class KrMonitoringRepository:
    """Berechnet kalenderjährliche KR-Ansicht aus vorhandenen OP-Daten."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_calendar_year_totals(
        self, *, company_id: UUID, calendar_year: int
    ) -> KrCalendarYearTotals:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if isinstance(calendar_year, bool) or not isinstance(calendar_year, int):
            raise TypeError("calendar_year must be an integer")
        start = date(calendar_year, 1, 1)
        end = date(calendar_year + 1, 1, 1)
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")

        payment_reversal = aliased(Buchung)
        reversed_payment = exists(
            select(payment_reversal.id).where(
                payment_reversal.reversal_of_booking_id == Zahlung.booking_id,
                payment_reversal.booking_type == BookingType.REVERSAL.value,
            )
        )
        payment_rows = (
            self._session.query(
                Zahlung.payment_id,
                Zahlung.amount,
                func.sum(RechnungsOPZahlungsereignis.amount).label("allocated"),
            )
            .join(
                RechnungsOPZahlungsereignis,
                RechnungsOPZahlungsereignis.payment_id == Zahlung.payment_id,
            )
            .join(
                ForderungsOP,
                ForderungsOP.open_item_id
                == RechnungsOPZahlungsereignis.receivable_open_item_id,
            )
            .join(
                Ausgangsrechnung,
                Ausgangsrechnung.invoice_id == ForderungsOP.invoice_id,
            )
            .join(Buchung, Buchung.booking_id == Zahlung.booking_id)
            .join(Wirtschaftsjahr, Wirtschaftsjahr.id == Buchung.wirtschaftsjahr_id)
            .filter(
                Zahlung.mandant_id == company.id,
                Zahlung.direction == "CUSTOMER_RECEIPT",
                Zahlung.payment_date >= start,
                Zahlung.payment_date < end,
                RechnungsOPZahlungsereignis.direction == "CUSTOMER_RECEIPT",
                RechnungsOPZahlungsereignis.receivable_open_item_id.is_not(None),
                Ausgangsrechnung.mandant_id == company.id,
                Ausgangsrechnung.partner_id == Zahlung.partner_id,
                Wirtschaftsjahr.mandant_id == company.id,
                Buchung.booking_type == BookingType.REGULAR.value,
                not_(reversed_payment),
            )
            .group_by(Zahlung.payment_id, Zahlung.amount)
            .all()
        )
        customer_payments = ZERO
        for _payment_id, payment_amount, allocated_amount in payment_rows:
            # One grouped row per payment; guard against legacy/corrupt events
            # so the total can never exceed the recorded cash receipt.
            customer_payments += min(Decimal(allocated_amount or ZERO), payment_amount)

        refund_reversal = aliased(Buchung)
        reversed_refund = exists(
            select(refund_reversal.id).where(
                refund_reversal.reversal_of_booking_id
                == GuthabenOPRueckerstattung.booking_id,
                refund_reversal.booking_type == BookingType.REVERSAL.value,
            )
        )
        returned_refund = exists(
            select(GuthabenOPRueckerstattungsruecknahme.id).where(
                GuthabenOPRueckerstattungsruecknahme.refund_id
                == GuthabenOPRueckerstattung.refund_id
            )
        )
        customer_credit_note_origin = exists(
            select(Gutschrift.id)
            .where(
                Gutschrift.credit_note_id == GuthabenOP.credit_note_id,
                Gutschrift.credit_note_kind == "CUSTOMER",
                Gutschrift.mandant_id == company.id,
            )
        )
        customer_cancellation_origin = exists(
            select(RechnungsOPStorno.id)
            .where(
                RechnungsOPStorno.storno_id == GuthabenOP.invoice_cancellation_id,
                RechnungsOPStorno.mandant_id == company.id,
                RechnungsOPStorno.receivable_invoice_id.is_not(None),
                RechnungsOPStorno.payable_invoice_id.is_(None),
            )
        )
        refund_rows = (
            self._session.query(GuthabenOPRueckerstattung.refund_id, GuthabenOPRueckerstattung.amount)
            .join(
                GuthabenOP,
                GuthabenOP.open_item_id == GuthabenOPRueckerstattung.open_item_id,
            )
            .join(
                Buchung,
                Buchung.booking_id == GuthabenOPRueckerstattung.booking_id,
            )
            .join(Wirtschaftsjahr, Wirtschaftsjahr.id == Buchung.wirtschaftsjahr_id)
            .filter(
                GuthabenOPRueckerstattung.mandant_id == company.id,
                GuthabenOPRueckerstattung.direction == "CUSTOMER",
                GuthabenOPRueckerstattung.refund_date >= start,
                GuthabenOPRueckerstattung.refund_date < end,
                Wirtschaftsjahr.mandant_id == company.id,
                Buchung.booking_type == BookingType.REGULAR.value,
                or_(customer_credit_note_origin, customer_cancellation_origin),
                not_(returned_refund),
                not_(reversed_refund),
            )
            .all()
        )
        # The refund_id primary business key is counted once, independent of
        # how many other records reference its credit open item.
        customer_refunds = sum(
            (amount for _refund_id, amount in {row[0]: row for row in refund_rows}.values()),
            start=ZERO,
        )
        has_direct_revenue_bookings = self._has_direct_revenue_booking(
            company_id=company.id,
            start=start,
            end=end,
        )
        return KrCalendarYearTotals(
            calendar_year=calendar_year,
            customer_payments=customer_payments,
            customer_refunds=customer_refunds,
            has_direct_revenue_bookings=has_direct_revenue_bookings,
        )

    def _has_direct_revenue_booking(
        self, *, company_id: int, start: date, end: date
    ) -> bool:
        op_source_booking_ids = select(Ausgangsrechnung.booking_id).where(
            Ausgangsrechnung.mandant_id == company_id
        ).union(
            select(Gutschrift.booking_id).where(
                Gutschrift.mandant_id == company_id,
                Gutschrift.credit_note_kind == "CUSTOMER",
            ),
            select(RechnungsOPStorno.booking_id).where(
                RechnungsOPStorno.mandant_id == company_id
            ),
            select(RechnungsOPStorno.credit_booking_id).where(
                RechnungsOPStorno.mandant_id == company_id,
                RechnungsOPStorno.credit_booking_id.is_not(None),
            ),
        )
        return (
            self._session.query(Buchung.id)
            .join(Wirtschaftsjahr, Wirtschaftsjahr.id == Buchung.wirtschaftsjahr_id)
            .join(Buchungszeile, Buchungszeile.buchung_id == Buchung.id)
            .join(
                Konto,
                and_(
                    Konto.mandant_id == company_id,
                    Konto.account_number == Buchungszeile.account_number,
                    Konto.account_type == AccountType.REVENUE.name,
                ),
            )
            .filter(
                Wirtschaftsjahr.mandant_id == company_id,
                Buchung.booking_date >= start,
                Buchung.booking_date < end,
                Buchung.booking_type.in_(
                    (BookingType.REGULAR.value, BookingType.REVERSAL.value)
                ),
                ~Buchung.booking_id.in_(op_source_booking_ids),
            )
            .first()
            is not None
        )
