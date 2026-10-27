"""Persistenz für Zahlungen und Rechnungs-OP-Zuordnungen."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Eingangsrechnung,
    ForderungsOP,
    Geschaeftspartner,
    Mandant,
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_payment import (
    OpenInvoiceSummary,
    OpenItemPayment,
    OpenItemPaymentEvent,
    PaymentDirection,
)


class OpenItemPaymentRepository:
    """Schreibt eine Zahlung und ihre OP-Zuordnungen in derselben Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        payment: OpenItemPayment,
        events: tuple[OpenItemPaymentEvent, ...],
        fiscal_year: FiscalYear,
        company_id: UUID,
        partner_id: UUID,
        commit: bool = True,
    ) -> None:
        if not isinstance(payment, OpenItemPayment):
            raise TypeError("payment must be an OpenItemPayment")
        if not isinstance(events, tuple) or not events:
            raise ValueError("Mindestens ein OP-Zahlungsereignis ist erforderlich.")
        if not all(isinstance(event, OpenItemPaymentEvent) for event in events):
            raise TypeError("events must contain OpenItemPaymentEvent values")
        if payment.company_id != company_id or payment.partner_id != partner_id:
            raise ValueError("Zahlung und Aufruf haben unterschiedliche Partnerbezüge.")
        if sum((event.amount for event in events), start=ZERO) != payment.amount:
            raise ValueError("Die Summe der OP-Zuordnungen muss exakt dem Zahlungsbetrag entsprechen.")
        if len({event.open_item_id for event in events}) != len(events):
            raise ValueError("Ein Rechnungs-OP darf pro Zahlung nur einmal zugeordnet werden.")
        for event in events:
            if event.payment_id != payment.payment_id:
                raise ValueError("Ein OP-Ereignis verweist auf eine andere Zahlung.")
            if event.direction is not payment.direction:
                raise ValueError("Zahlungsrichtung und OP-Zuordnung stimmen nicht überein.")
            if event.effective_date != payment.payment_date:
                raise ValueError("Ereignisdatum und tatsächliches Zahlungsdatum stimmen nicht überein.")

        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id == company.id,
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
            .one_or_none()
        )
        if fiscal_year_model is None:
            raise ValueError("Das Geschäftsjahr gehört nicht zum Mandanten.")

        if self._session.query(Zahlung.id).filter(
            Zahlung.payment_id == str(payment.payment_id)
        ).one_or_none():
            raise ValueError("Die Zahlungs-ID ist bereits vorhanden.")
        event_id_values = [str(event.event_id) for event in events]
        if len(set(event_id_values)) != len(event_id_values):
            raise ValueError("OP-Ereignis-IDs müssen eindeutig sein.")
        if self._session.query(RechnungsOPZahlungsereignis.id).filter(
            RechnungsOPZahlungsereignis.event_id.in_(event_id_values)
        ).first():
            raise ValueError("Eine OP-Ereignis-ID ist bereits vorhanden.")
        if self._session.query(Zahlung.id).filter(
            Zahlung.booking_id == str(payment.booking_id)
        ).one_or_none():
            raise ValueError("Für diese Buchung existiert bereits eine Zahlung.")

        for event in sorted(events, key=lambda item: str(item.open_item_id)):
            invoice = self.get_open_invoice(
                company_id=company_id,
                open_item_id=event.open_item_id,
                direction=payment.direction,
                for_update=True,
            )
            if invoice is None:
                raise ValueError("Ein Rechnungs-OP ist nicht vorhanden.")
            self.ensure_not_cancelled(
                open_item_id=event.open_item_id,
                direction=payment.direction,
            )
            if invoice.partner_id != partner_id:
                raise ValueError("Alle Rechnungs-OPs müssen demselben Geschäftspartner gehören.")
            if invoice.open_amount <= ZERO:
                raise ValueError("Ein Rechnungs-OP ist bereits vollständig ausgeglichen.")
            if event.amount > invoice.open_amount:
                raise ValueError(
                    f"Die Zuordnung übersteigt den offenen Rechnungsbetrag "
                    f"({invoice.document_number}: {invoice.open_amount:.2f})."
                )

        booking = (
            self._session.query(Buchung.id)
            .filter(
                Buchung.booking_id == str(payment.booking_id),
                Buchung.wirtschaftsjahr_id == fiscal_year_model.id,
            )
            .one_or_none()
        )
        if booking is None:
            raise ValueError(
                "Die Hauptbuchbuchung fehlt oder gehört zu einem anderen Geschäftsjahr."
            )
        partner_role = (
            Geschaeftspartner.is_customer
            if payment.direction is PaymentDirection.CUSTOMER_RECEIPT
            else Geschaeftspartner.is_supplier
        )
        partner = (
            self._session.query(Geschaeftspartner.id)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(partner_id),
                partner_role.is_(True),
            )
            .one_or_none()
        )
        if partner is None:
            raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")

        self._session.add(
            Zahlung(
                payment_id=str(payment.payment_id),
                mandant_id=company.id,
                partner_id=str(payment.partner_id),
                direction=payment.direction.value,
                amount=payment.amount,
                payment_date=payment.payment_date,
                recorded_at=payment.recorded_at,
                booking_id=str(payment.booking_id),
            )
        )
        self._session.flush()
        self._session.add_all(
            [
                RechnungsOPZahlungsereignis(
                event_id=str(event.event_id),
                payment_id=str(event.payment_id),
                direction=event.direction.value,
                receivable_open_item_id=(
                    str(event.open_item_id)
                    if event.direction is PaymentDirection.CUSTOMER_RECEIPT
                    else None
                ),
                payable_open_item_id=(
                    str(event.open_item_id)
                    if event.direction is PaymentDirection.SUPPLIER_PAYMENT
                    else None
                ),
                amount=event.amount,
                effective_date=event.effective_date,
            )
                for event in events
            ]
        )
        if commit:
            self._session.commit()

    def get_open_invoice(
        self,
        *,
        company_id: UUID,
        open_item_id: UUID,
        direction: PaymentDirection,
        for_update: bool = False,
    ) -> OpenInvoiceSummary | None:
        if not isinstance(direction, PaymentDirection):
            raise TypeError("direction must be a PaymentDirection")
        if direction is PaymentDirection.CUSTOMER_RECEIPT:
            open_item_query = self._session.query(ForderungsOP).filter(
                ForderungsOP.open_item_id == str(open_item_id)
            )
            if for_update:
                open_item_query = open_item_query.with_for_update()
            open_item = open_item_query.one_or_none()
            if open_item is None:
                return None
            invoice = (
                self._session.query(Ausgangsrechnung)
                .filter(Ausgangsrechnung.invoice_id == open_item.invoice_id)
                .one()
            )
            allocated = (
                self._session.query(func.sum(RechnungsOPZahlungsereignis.amount))
                .filter(
                    RechnungsOPZahlungsereignis.receivable_open_item_id
                    == str(open_item_id)
                )
                .scalar()
            )
            offset_allocated = (
                self._session.query(
                    func.sum(RechnungsOPVerrechnungsereignis.amount)
                )
                .filter(
                    RechnungsOPVerrechnungsereignis.receivable_open_item_id
                    == str(open_item_id)
                )
                .scalar()
            )
            correction_delta = self._session.query(
                func.sum(Zahlungszuordnungskorrekturereignis.amount_delta)
            ).filter(
                Zahlungszuordnungskorrekturereignis.receivable_open_item_id
                == str(open_item_id)
            ).scalar()
            storno_amount = self._session.query(
                func.sum(RechnungsOPStorno.amount)
            ).filter(
                RechnungsOPStorno.receivable_open_item_id == str(open_item_id)
            ).scalar()
            original_amount = open_item.amount
            direction_label = PaymentDirection.CUSTOMER_RECEIPT
        else:
            open_item_query = self._session.query(VerbindlichkeitsOP).filter(
                VerbindlichkeitsOP.open_item_id == str(open_item_id)
            )
            if for_update:
                open_item_query = open_item_query.with_for_update()
            open_item = open_item_query.one_or_none()
            if open_item is None:
                return None
            invoice = (
                self._session.query(Eingangsrechnung)
                .filter(Eingangsrechnung.invoice_id == open_item.invoice_id)
                .one()
            )
            allocated = (
                self._session.query(func.sum(RechnungsOPZahlungsereignis.amount))
                .filter(
                    RechnungsOPZahlungsereignis.payable_open_item_id
                    == str(open_item_id)
                )
                .scalar()
            )
            offset_allocated = (
                self._session.query(
                    func.sum(RechnungsOPVerrechnungsereignis.amount)
                )
                .filter(
                    RechnungsOPVerrechnungsereignis.payable_open_item_id
                    == str(open_item_id)
                )
                .scalar()
            )
            correction_delta = self._session.query(
                func.sum(Zahlungszuordnungskorrekturereignis.amount_delta)
            ).filter(
                Zahlungszuordnungskorrekturereignis.payable_open_item_id
                == str(open_item_id)
            ).scalar()
            storno_amount = self._session.query(
                func.sum(RechnungsOPStorno.amount)
            ).filter(
                RechnungsOPStorno.payable_open_item_id == str(open_item_id)
            ).scalar()
            original_amount = open_item.amount
            direction_label = PaymentDirection.SUPPLIER_PAYMENT

        company = (
            self._session.query(Mandant)
            .filter(Mandant.id == invoice.mandant_id)
            .one()
        )
        if company.company_id != str(company_id):
            raise ValueError("Der Rechnungs-OP gehört nicht zum geöffneten Mandanten.")
        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == invoice.partner_id,
            )
            .one_or_none()
        )
        if partner is None:
            raise ValueError("Der Rechnungs-OP verweist auf keinen Geschäftspartner.")
        partner_role = (
            partner.is_customer
            if direction_label is PaymentDirection.CUSTOMER_RECEIPT
            else partner.is_supplier
        )
        if not partner_role:
            raise ValueError("Der Geschäftspartner hat nicht die zum Rechnungs-OP passende Rolle.")
        open_amount = original_amount - (allocated or ZERO) - (
            offset_allocated or ZERO
        ) - (correction_delta or ZERO)
        open_amount -= storno_amount or ZERO
        if open_amount < ZERO:
            raise ValueError(
                "Zahlungs- und Verrechnungsereignisse überschreiten den "
                "Ursprungsbetrag des Rechnungs-OPs."
            )
        return OpenInvoiceSummary(
            company_id=company_id,
            partner_id=UUID(invoice.partner_id),
            open_item_id=open_item_id,
            direction=direction_label,
            document_number=invoice.invoice_number,
            document_date=invoice.invoice_date,
            due_date=invoice.due_date,
            original_amount=original_amount,
            open_amount=open_amount,
            partner_name=partner.name,
        )

    def ensure_not_cancelled(
        self,
        *,
        open_item_id: UUID,
        direction: PaymentDirection,
    ) -> None:
        """Verhindert neue OP-Bewegungen auf einer bereits stornierten Rechnung."""
        if direction is PaymentDirection.CUSTOMER_RECEIPT:
            query = self._session.query(RechnungsOPStorno.id).filter(
                RechnungsOPStorno.receivable_open_item_id == str(open_item_id)
            )
        elif direction is PaymentDirection.SUPPLIER_PAYMENT:
            query = self._session.query(RechnungsOPStorno.id).filter(
                RechnungsOPStorno.payable_open_item_id == str(open_item_id)
            )
        else:
            raise TypeError("direction must be a PaymentDirection")
        if query.first():
            raise ValueError("Der Rechnungs-OP wurde bereits storniert und kann nicht erneut verwendet werden.")

    def list_open_invoices(self, company_id: UUID) -> tuple[OpenInvoiceSummary, ...]:
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            return ()
        summaries: list[OpenInvoiceSummary] = []
        for open_item in (
            self._session.query(ForderungsOP)
            .join(Ausgangsrechnung)
            .filter(Ausgangsrechnung.mandant_id == company.id)
            .all()
        ):
            summary = self.get_open_invoice(
                company_id=company_id,
                open_item_id=UUID(open_item.open_item_id),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
            )
            if summary is not None and summary.open_amount > ZERO:
                summaries.append(summary)
        for open_item in (
            self._session.query(VerbindlichkeitsOP)
            .join(Eingangsrechnung)
            .filter(Eingangsrechnung.mandant_id == company.id)
            .all()
        ):
            summary = self.get_open_invoice(
                company_id=company_id,
                open_item_id=UUID(open_item.open_item_id),
                direction=PaymentDirection.SUPPLIER_PAYMENT,
            )
            if summary is not None and summary.open_amount > ZERO:
                summaries.append(summary)
        return tuple(summaries)
