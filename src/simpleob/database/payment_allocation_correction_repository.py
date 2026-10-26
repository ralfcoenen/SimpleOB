"""Persistenz für unveränderliche Korrekturen von Zahlungszuordnungen."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Eingangsrechnung,
    ForderungsOP,
    Mandant,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.payment_allocation_correction import (
    CorrectablePaymentAllocation,
    PaymentAllocationCorrection,
)


class PaymentAllocationCorrectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_correctable(
        self, *, company_id: UUID, event_id: UUID, for_update: bool = False
    ) -> CorrectablePaymentAllocation | None:
        query = self._session.query(RechnungsOPZahlungsereignis).filter_by(
            event_id=str(event_id)
        )
        if for_update:
            query = query.with_for_update()
        event = query.one_or_none()
        if event is None:
            return None
        payment = self._session.query(Zahlung).filter_by(payment_id=event.payment_id).one()
        company = self._session.query(Mandant).filter_by(id=payment.mandant_id).one()
        if company.company_id != str(company_id):
            raise ValueError("Die Zahlungszuordnung gehört nicht zum geöffneten Mandanten.")
        direction = PaymentDirection(event.direction)
        item_id = event.receivable_open_item_id if direction is PaymentDirection.CUSTOMER_RECEIPT else event.payable_open_item_id
        item_model = ForderungsOP if direction is PaymentDirection.CUSTOMER_RECEIPT else VerbindlichkeitsOP
        invoice_model = Ausgangsrechnung if direction is PaymentDirection.CUSTOMER_RECEIPT else Eingangsrechnung
        item = self._session.query(item_model).filter_by(open_item_id=item_id).one()
        invoice = self._session.query(invoice_model).filter_by(invoice_id=item.invoice_id).one()
        if invoice.mandant_id != payment.mandant_id or invoice.partner_id != payment.partner_id:
            raise ValueError("Zahlungszuordnung, Rechnung und Geschäftspartner stimmen nicht überein.")
        corrected = self._session.query(func.sum(Zahlungszuordnungskorrektur.amount)).filter_by(
            original_allocation_event_id=event.event_id
        ).scalar() or ZERO
        return CorrectablePaymentAllocation(
            company_id=company_id, partner_id=UUID(payment.partner_id), payment_id=UUID(payment.payment_id),
            payment_date=payment.payment_date, direction=direction, original_event_id=UUID(event.event_id),
            original_amount=event.amount, corrected_amount=corrected,
            correctable_amount=event.amount-corrected, source_open_item_id=UUID(item_id),
            source_document_number=invoice.invoice_number,
        )

    def list_correctable(self, company_id: UUID) -> tuple[CorrectablePaymentAllocation, ...]:
        rows = (self._session.query(RechnungsOPZahlungsereignis.event_id)
                .join(Zahlung, Zahlung.payment_id == RechnungsOPZahlungsereignis.payment_id)
                .join(Mandant, Mandant.id == Zahlung.mandant_id)
                .filter(Mandant.company_id == str(company_id)).all())
        result = []
        for (event_id,) in rows:
            item = self.get_correctable(company_id=company_id, event_id=UUID(event_id))
            if item is not None and item.correctable_amount > ZERO:
                result.append(item)
        return tuple(result)

    def add(self, *, correction: PaymentAllocationCorrection, fiscal_year: FiscalYear, commit: bool = True) -> None:
        company = self._session.query(Mandant).filter_by(company_id=str(correction.company_id)).one_or_none()
        if company is None:
            raise ValueError("Der Mandant ist nicht vorhanden.")
        fy = self._session.query(Wirtschaftsjahr).filter_by(
            mandant_id=company.id, start_date=fiscal_year.start_date, end_date=fiscal_year.end_date
        ).one_or_none()
        if (
            fy is None
            or fy.status == FiscalYearStatus.CLOSED.value
            or not fiscal_year.contains(correction.correction_date)
        ):
            raise ValueError("Korrekturdatum oder Geschäftsjahr ist für diesen Mandanten ungültig.")
        candidate = self.get_correctable(
            company_id=correction.company_id,
            event_id=correction.original_event_id,
            for_update=True,
        )
        if candidate is None or candidate.correctable_amount < correction.amount:
            raise ValueError("Der Betrag übersteigt den noch korrigierbaren Anteil der Zuordnung.")
        if candidate.payment_id != correction.payment_id or candidate.partner_id != correction.partner_id or candidate.direction is not correction.direction or candidate.source_open_item_id != correction.source_open_item_id:
            raise ValueError("Die Korrektur stimmt nicht mit der ursprünglichen Zahlungszuordnung überein.")
        model = Zahlungszuordnungskorrektur(
            correction_id=str(correction.correction_id), mandant_id=company.id,
            partner_id=str(correction.partner_id), direction=correction.direction.value,
            original_payment_id=str(correction.payment_id), original_allocation_event_id=str(correction.original_event_id),
            source_receivable_open_item_id=str(correction.source_open_item_id) if correction.direction is PaymentDirection.CUSTOMER_RECEIPT else None,
            source_payable_open_item_id=str(correction.source_open_item_id) if correction.direction is PaymentDirection.SUPPLIER_PAYMENT else None,
            target_receivable_open_item_id=str(correction.target_open_item_id) if correction.direction is PaymentDirection.CUSTOMER_RECEIPT else None,
            target_payable_open_item_id=str(correction.target_open_item_id) if correction.direction is PaymentDirection.SUPPLIER_PAYMENT else None,
            amount=correction.amount, correction_date=correction.correction_date,
            recorded_at=correction.recorded_at, reason=correction.reason, booking_id=str(correction.booking_id) if correction.booking_id else None,
        )
        self._session.add(model)
        self._session.flush()
        for role, item_id, delta, event_id in (
            ("SOURCE_RELEASE", correction.source_open_item_id, -correction.amount, correction.source_event_id),
            ("TARGET_APPLY", correction.target_open_item_id, correction.amount, correction.target_event_id),
        ):
            self._session.add(Zahlungszuordnungskorrekturereignis(
                event_id=str(event_id), correction_id=str(correction.correction_id), event_role=role,
                direction=correction.direction.value,
                receivable_open_item_id=str(item_id) if correction.direction is PaymentDirection.CUSTOMER_RECEIPT else None,
                payable_open_item_id=str(item_id) if correction.direction is PaymentDirection.SUPPLIER_PAYMENT else None,
                amount_delta=delta, effective_date=correction.correction_date,
            ))
        if commit:
            self._session.commit()
