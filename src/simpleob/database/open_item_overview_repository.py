"""Lesende Abfragen für die aktuelle OP-Übersicht."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Eingangsrechnung,
    ForderungsOP,
    Geschaeftspartner,
    GuthabenOP,
    GuthabenOPEreignis,
    GuthabenOPRueckerstattung,
    GuthabenOPRueckerstattungsruecknahme,
    Gutschrift,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_overview import (
    OpenItemActivity,
    OpenItemActivityKind,
    OpenItemKind,
    OpenItemOverviewDetail,
    OpenItemOverviewItem,
    OpenItemOverviewReport,
    OpenItemPartnerOption,
)
from simpleob.domain.open_item_payment import PaymentDirection


class OpenItemOverviewRepository:
    """Lädt aktuelle OPs über vorhandene Restbetrags-Repositories."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._payment_repository = OpenItemPaymentRepository(session)
        self._offset_repository = OpenItemOffsetRepository(session)
        self._partner_repository = BusinessPartnerRepository(session)

    def list_items(
        self,
        *,
        company_id: UUID,
        include_settled: bool = False,
    ) -> OpenItemOverviewReport:
        company = self._company(company_id)
        partners = tuple(
            OpenItemPartnerOption(partner.partner_id, partner.name)
            for partner in self._partner_repository.list_for_company(
                company_id,
                active_only=False,
            )
        )
        items: list[OpenItemOverviewItem] = []

        receivable_rows = (
            self._session.query(ForderungsOP, Ausgangsrechnung, Buchung)
            .join(
                Ausgangsrechnung,
                ForderungsOP.invoice_id == Ausgangsrechnung.invoice_id,
            )
            .join(Buchung, Ausgangsrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                Ausgangsrechnung.mandant_id == company.id,
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .all()
        )
        for open_item, invoice, booking in receivable_rows:
            item = self._invoice_item(
                company_id=company_id,
                open_item=open_item,
                invoice=invoice,
                booking=booking,
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                kind=OpenItemKind.CUSTOMER_RECEIVABLE,
            )
            if include_settled or item.open_amount > ZERO:
                items.append(item)

        payable_rows = (
            self._session.query(VerbindlichkeitsOP, Eingangsrechnung, Buchung)
            .join(
                Eingangsrechnung,
                VerbindlichkeitsOP.invoice_id == Eingangsrechnung.invoice_id,
            )
            .join(Buchung, Eingangsrechnung.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                Eingangsrechnung.mandant_id == company.id,
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .all()
        )
        for open_item, invoice, booking in payable_rows:
            item = self._invoice_item(
                company_id=company_id,
                open_item=open_item,
                invoice=invoice,
                booking=booking,
                direction=PaymentDirection.SUPPLIER_PAYMENT,
                kind=OpenItemKind.SUPPLIER_PAYABLE,
            )
            if include_settled or item.open_amount > ZERO:
                items.append(item)

        credit_rows = (
            self._session.query(GuthabenOP, Gutschrift, Buchung)
            .join(Gutschrift, GuthabenOP.credit_note_id == Gutschrift.credit_note_id)
            .join(Buchung, Gutschrift.booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                Gutschrift.mandant_id == company.id,
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .all()
        )
        for open_item, credit_note, booking in credit_rows:
            direction = (
                OffsetDirection.CUSTOMER
                if credit_note.credit_note_kind == "CUSTOMER"
                else OffsetDirection.SUPPLIER
            )
            kind = (
                OpenItemKind.CUSTOMER_CREDIT
                if direction is OffsetDirection.CUSTOMER
                else OpenItemKind.SUPPLIER_CREDIT
            )
            credit = self._offset_repository.get_credit(
                company_id=company_id,
                partner_id=UUID(credit_note.partner_id),
                open_item_id=UUID(open_item.open_item_id),
                direction=direction,
            )
            if credit is None:
                continue
            refunds_amount = self._credit_refund_amount(open_item.open_item_id)
            item = OpenItemOverviewItem(
                company_id=company_id,
                partner_id=credit.partner_id,
                partner_name=self._partner_name(company.id, credit_note.partner_id),
                open_item_id=credit.open_item_id,
                kind=kind,
                document_number=credit_note.note_number,
                document_date=credit_note.note_date,
                booking_date=booking.booking_date,
                due_date=None,
                original_amount=credit.original_amount,
                payments_amount=ZERO,
                offsets_amount=(
                    credit.original_amount - credit.available_amount - refunds_amount
                ),
                open_amount=credit.available_amount,
                source_booking_id=credit_note.booking_id,
                refunds_amount=refunds_amount,
            )
            if include_settled or item.open_amount > ZERO:
                items.append(item)

        cancellation_credit_rows = (
            self._session.query(GuthabenOP, RechnungsOPStorno, Buchung)
            .join(
                RechnungsOPStorno,
                GuthabenOP.invoice_cancellation_id == RechnungsOPStorno.storno_id,
            )
            .join(Buchung, RechnungsOPStorno.credit_booking_id == Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                RechnungsOPStorno.mandant_id == company.id,
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .all()
        )
        for open_item, cancellation, booking in cancellation_credit_rows:
            if cancellation.receivable_invoice_id is not None:
                direction = OffsetDirection.CUSTOMER
                invoice = (
                    self._session.query(Ausgangsrechnung)
                    .filter(
                        Ausgangsrechnung.invoice_id
                        == cancellation.receivable_invoice_id
                    )
                    .one_or_none()
                )
            else:
                direction = OffsetDirection.SUPPLIER
                invoice = (
                    self._session.query(Eingangsrechnung)
                    .filter(
                        Eingangsrechnung.invoice_id == cancellation.payable_invoice_id
                    )
                    .one_or_none()
                )
            if invoice is None or invoice.mandant_id != company.id:
                continue
            credit = self._offset_repository.get_credit(
                company_id=company_id,
                partner_id=UUID(cancellation.partner_id),
                open_item_id=UUID(open_item.open_item_id),
                direction=direction,
            )
            if credit is None:
                continue
            refunds_amount = self._credit_refund_amount(open_item.open_item_id)
            kind = (
                OpenItemKind.CUSTOMER_CREDIT
                if direction is OffsetDirection.CUSTOMER
                else OpenItemKind.SUPPLIER_CREDIT
            )
            item = OpenItemOverviewItem(
                company_id=company_id,
                partner_id=credit.partner_id,
                partner_name=self._partner_name(company.id, cancellation.partner_id),
                open_item_id=credit.open_item_id,
                kind=kind,
                document_number=credit.document_number,
                document_date=invoice.invoice_date,
                booking_date=booking.booking_date,
                due_date=None,
                original_amount=credit.original_amount,
                payments_amount=ZERO,
                offsets_amount=(
                    credit.original_amount - credit.available_amount - refunds_amount
                ),
                open_amount=credit.available_amount,
                source_booking_id=cancellation.credit_booking_id,
                refunds_amount=refunds_amount,
            )
            if include_settled or item.open_amount > ZERO:
                items.append(item)

        items.sort(
            key=lambda item: (
                item.partner_name.casefold(),
                item.kind.value,
                item.document_date,
                item.document_number.casefold(),
            )
        )
        return OpenItemOverviewReport(
            company_id=company_id,
            partners=partners,
            items=tuple(items),
            include_settled=include_settled,
        )

    def get_detail(
        self,
        *,
        company_id: UUID,
        open_item_id: UUID,
    ) -> OpenItemOverviewDetail | None:
        report = self.list_items(company_id=company_id, include_settled=True)
        item = next(
            (row for row in report.items if row.open_item_id == open_item_id),
            None,
        )
        if item is None:
            return None

        cancellation_credit_id = (
            self._session.query(GuthabenOP.invoice_cancellation_id)
            .filter(GuthabenOP.open_item_id == str(open_item_id))
            .scalar()
        )
        is_cancellation_credit = cancellation_credit_id is not None
        activities = [
            OpenItemActivity(
                kind=OpenItemActivityKind.ORIGINAL,
                activity_date=(item.booking_date if is_cancellation_credit else item.document_date),
                booking_date=item.booking_date,
                amount=item.original_amount,
                reference=item.document_number,
                description=(
                    f"Guthaben aus Rechnungsstorno – {item.document_number}"
                    if is_cancellation_credit
                    else f"Ursprungsbeleg – {item.kind.label}"
                ),
                booking_id=item.source_booking_id,
            )
        ]
        if item.kind in (
            OpenItemKind.CUSTOMER_RECEIVABLE,
            OpenItemKind.SUPPLIER_PAYABLE,
        ):
            activities.extend(self._invoice_activities(item))
        else:
            activities.extend(self._credit_activities(item))

        activities.sort(
            key=lambda activity: (
                activity.booking_date or activity.activity_date,
                activity.recorded_at.isoformat() if activity.recorded_at else "",
                {
                    OpenItemActivityKind.ORIGINAL: 0,
                    OpenItemActivityKind.PAYMENT: 1,
                    OpenItemActivityKind.OFFSET: 2,
                    OpenItemActivityKind.PAYMENT_CORRECTION: 3,
                    OpenItemActivityKind.INVOICE_CANCELLATION: 4,
                    OpenItemActivityKind.REFUND: 5,
                    OpenItemActivityKind.REFUND_REVERSAL: 6,
                }[activity.kind],
                activity.reference,
            )
        )
        return OpenItemOverviewDetail(item=item, activities=tuple(activities))

    def _invoice_item(
        self,
        *,
        company_id: UUID,
        open_item,
        invoice,
        booking: Buchung,
        direction: PaymentDirection,
        kind: OpenItemKind,
    ) -> OpenItemOverviewItem:
        summary = self._payment_repository.get_open_invoice(
            company_id=company_id,
            open_item_id=UUID(open_item.open_item_id),
            direction=direction,
        )
        if summary is None:
            raise ValueError("Der Rechnungs-OP ist nicht vorhanden.")
        offset_column = (
            RechnungsOPVerrechnungsereignis.receivable_open_item_id
            if direction is PaymentDirection.CUSTOMER_RECEIPT
            else RechnungsOPVerrechnungsereignis.payable_open_item_id
        )
        offsets_amount = (
            self._session.query(func.sum(RechnungsOPVerrechnungsereignis.amount))
            .filter(offset_column == open_item.open_item_id)
            .scalar()
            or ZERO
        )
        storno_column = (
            RechnungsOPStorno.receivable_open_item_id
            if direction is PaymentDirection.CUSTOMER_RECEIPT
            else RechnungsOPStorno.payable_open_item_id
        )
        storno_closed_amount = (
            self._session.query(func.sum(RechnungsOPStorno.closed_open_amount))
            .filter(storno_column == open_item.open_item_id)
            .scalar()
            or ZERO
        )
        # The existing repository owns the residual calculation, including
        # payment allocation corrections. This derives its net payment part.
        payments_amount = (
            summary.original_amount
            - offsets_amount
            - storno_closed_amount
            - summary.open_amount
        )
        return OpenItemOverviewItem(
            company_id=company_id,
            partner_id=summary.partner_id,
            partner_name=summary.partner_name,
            open_item_id=summary.open_item_id,
            kind=kind,
            document_number=summary.document_number,
            document_date=summary.document_date,
            booking_date=booking.booking_date,
            due_date=summary.due_date,
            original_amount=summary.original_amount,
            payments_amount=payments_amount,
            offsets_amount=offsets_amount,
            open_amount=summary.open_amount,
            source_booking_id=invoice.booking_id,
        )

    def _invoice_activities(
        self,
        item: OpenItemOverviewItem,
    ) -> list[OpenItemActivity]:
        receivable = item.kind is OpenItemKind.CUSTOMER_RECEIVABLE
        payment_item_column = (
            RechnungsOPZahlungsereignis.receivable_open_item_id
            if receivable
            else RechnungsOPZahlungsereignis.payable_open_item_id
        )
        payment_rows = (
            self._session.query(RechnungsOPZahlungsereignis, Zahlung, Buchung)
            .join(Zahlung, RechnungsOPZahlungsereignis.payment_id == Zahlung.payment_id)
            .join(Buchung, Zahlung.booking_id == Buchung.booking_id)
            .filter(payment_item_column == str(item.open_item_id))
            .all()
        )
        activities = [
            OpenItemActivity(
                kind=OpenItemActivityKind.PAYMENT,
                activity_date=payment.payment_date,
                booking_date=booking.booking_date,
                amount=event.amount,
                reference=(
                    f"{'Kundenzahlung' if receivable else 'Lieferantenzahlung'} · "
                    f"{item.partner_name} · Rechnung {item.document_number}"
                    + (
                        f" · Beleg {booking.voucher_no}"
                        if booking.voucher_no
                        else ""
                    )
                ),
                description=(
                    f"Zuordnung {event.amount:.2f} EUR aus tatsächlicher "
                    f"Zahlung über {payment.amount:.2f} EUR; erfasst "
                    f"{payment.recorded_at:%d.%m.%Y %H:%M:%S}"
                ),
                booking_id=payment.booking_id,
                payment_id=payment.payment_id,
                recorded_at=payment.recorded_at,
                payment_total=payment.amount,
            )
            for event, payment, booking in payment_rows
        ]

        offset_item_column = (
            RechnungsOPVerrechnungsereignis.receivable_open_item_id
            if receivable
            else RechnungsOPVerrechnungsereignis.payable_open_item_id
        )
        offset_rows = (
            self._session.query(
                RechnungsOPVerrechnungsereignis,
                OPGuthabenverrechnung,
                Buchung,
            )
            .join(
                OPGuthabenverrechnung,
                RechnungsOPVerrechnungsereignis.settlement_id
                == OPGuthabenverrechnung.settlement_id,
            )
            .join(Buchung, OPGuthabenverrechnung.booking_id == Buchung.booking_id)
            .filter(offset_item_column == str(item.open_item_id))
            .all()
        )
        activities.extend(
            OpenItemActivity(
                kind=OpenItemActivityKind.OFFSET,
                activity_date=settlement.settlement_date,
                booking_date=booking.booking_date,
                amount=event.amount,
                reference=(
                    "Gutschriftenverrechnung · Gutschrift "
                    f"{self._credit_note_number(settlement.credit_open_item_id)}"
                ),
                description=(
                    f"{item.partner_name}: Rechnung {item.document_number} "
                    f"mit Gutschrift verrechnet"
                ),
                booking_id=settlement.booking_id,
                recorded_at=settlement.recorded_at,
            )
            for event, settlement, booking in offset_rows
        )

        correction_item_column = (
            Zahlungszuordnungskorrekturereignis.receivable_open_item_id
            if receivable
            else Zahlungszuordnungskorrekturereignis.payable_open_item_id
        )
        storno_item_column = (
            RechnungsOPStorno.receivable_open_item_id
            if receivable
            else RechnungsOPStorno.payable_open_item_id
        )
        correction_rows = (
            self._session.query(
                Zahlungszuordnungskorrekturereignis,
                Zahlungszuordnungskorrektur,
            )
            .join(
                Zahlungszuordnungskorrektur,
                Zahlungszuordnungskorrekturereignis.correction_id
                == Zahlungszuordnungskorrektur.correction_id,
            )
            .filter(correction_item_column == str(item.open_item_id))
            .all()
        )
        for event, correction in correction_rows:
            payment = (
                self._session.query(Zahlung)
                .filter(Zahlung.payment_id == correction.original_payment_id)
                .one_or_none()
            )
            booking = None
            payment_booking = None
            if correction.booking_id is not None:
                booking = (
                    self._session.query(Buchung)
                    .filter(Buchung.booking_id == correction.booking_id)
                    .one_or_none()
                )
            if payment is not None:
                payment_booking = (
                    self._session.query(Buchung)
                    .filter(Buchung.booking_id == payment.booking_id)
                    .one_or_none()
                )
            is_source = event.event_role == "SOURCE_RELEASE"
            if is_source:
                counterpart_open_item_id = (
                    correction.target_receivable_open_item_id
                    or correction.target_payable_open_item_id
                )
            else:
                counterpart_open_item_id = (
                    correction.source_receivable_open_item_id
                    or correction.source_payable_open_item_id
                )
            counterpart_number = self._invoice_number_for_open_item(
                counterpart_open_item_id,
                receivable=receivable,
            )
            role_description = (
                (
                    f"Zuordnung von Rechnung {item.document_number} auf "
                    f"Rechnung {counterpart_number} übertragen"
                )
                if is_source
                else (
                    f"Zuordnung von Rechnung {counterpart_number} auf "
                    f"Rechnung {item.document_number} übertragen"
                )
            )
            payment_dates = (
                f" · ursprüngliche Zahlung {payment.payment_date:%d.%m.%Y}"
                if payment is not None
                else ""
            )
            payment_booking_date = (
                f"Buchung der ursprünglichen Zahlung "
                f"{payment_booking.booking_date:%d.%m.%Y}"
                if payment_booking is not None
                else "Buchungsdatum der ursprünglichen Zahlung unbekannt"
            )
            activities.append(
                OpenItemActivity(
                    kind=OpenItemActivityKind.PAYMENT_CORRECTION,
                    activity_date=correction.correction_date,
                    booking_date=correction.booking_date,
                    amount=event.amount_delta,
                    reference=(
                        f"Zahlungszuordnungskorrektur · {item.partner_name} · "
                        f"Rechnung {item.document_number}"
                        f"{payment_dates}"
                    ),
                    description=(
                        f"{role_description}; {payment_booking_date}; "
                        f"keine neue Bank-/Kassenbewegung. "
                        f"Begründung: {correction.reason}"
                    ),
                    booking_id=(
                        correction.booking_id if booking is not None else None
                    ),
                    payment_id=correction.original_payment_id,
                    recorded_at=correction.recorded_at,
                )
            )

        storno_rows = (
            self._session.query(RechnungsOPStorno, Buchung)
            .join(Buchung, RechnungsOPStorno.booking_id == Buchung.booking_id)
            .filter(storno_item_column == str(item.open_item_id))
            .all()
        )
        activities.extend(
            OpenItemActivity(
                kind=OpenItemActivityKind.INVOICE_CANCELLATION,
                activity_date=booking.booking_date,
                booking_date=booking.booking_date,
                amount=-storno.closed_open_amount,
                reference=(
                    f"Rechnungsstorno · {item.partner_name} · "
                    f"Rechnung {item.document_number}"
                ),
                description=(
                    f"OP-Schließung durch Hauptbuchgegenbuchung vom "
                    f"{booking.booking_date:%d.%m.%Y}; "
                    f"Grund: {storno.reason}"
                ),
                booking_id=storno.booking_id,
                recorded_at=storno.recorded_at,
            )
            for storno, booking in storno_rows
        )
        return activities

    def _credit_activities(
        self,
        item: OpenItemOverviewItem,
    ) -> list[OpenItemActivity]:
        rows = (
            self._session.query(GuthabenOPEreignis, OPGuthabenverrechnung, Buchung)
            .join(
                OPGuthabenverrechnung,
                GuthabenOPEreignis.settlement_id
                == OPGuthabenverrechnung.settlement_id,
            )
            .join(Buchung, OPGuthabenverrechnung.booking_id == Buchung.booking_id)
            .filter(
                GuthabenOPEreignis.open_item_id == str(item.open_item_id),
                GuthabenOPEreignis.settlement_id.is_not(None),
            )
            .all()
        )
        credit_reference = (
            f"Rechnungsstorno {item.document_number.removeprefix('Storno ')}"
            if item.document_number.startswith("Storno ")
            else f"Gutschrift {item.document_number}"
        )
        activities = [
            OpenItemActivity(
                kind=OpenItemActivityKind.OFFSET,
                activity_date=settlement.settlement_date,
                booking_date=booking.booking_date,
                amount=-event.amount_delta,
                reference=(
                    f"Guthabenverrechnung · {credit_reference} "
                    f"mit Rechnung {self._invoice_number_for_open_item(
                        settlement.receivable_open_item_id
                        or settlement.payable_open_item_id,
                        receivable=settlement.direction == "CUSTOMER",
                    )}"
                ),
                description=f"{item.partner_name}: Guthaben verrechnet",
                booking_id=settlement.booking_id,
                recorded_at=settlement.recorded_at,
            )
            for event, settlement, booking in rows
        ]
        refund_rows = (
            self._session.query(GuthabenOPRueckerstattung, Buchung)
            .join(Buchung, GuthabenOPRueckerstattung.booking_id == Buchung.booking_id)
            .filter(
                GuthabenOPRueckerstattung.open_item_id == str(item.open_item_id),
                GuthabenOPRueckerstattung.mandant_id
                == self._session.query(Mandant.id)
                .filter(Mandant.company_id == str(item.company_id))
                .scalar_subquery(),
            )
            .all()
        )
        activities.extend(
            OpenItemActivity(
                kind=OpenItemActivityKind.REFUND,
                activity_date=refund.refund_date,
                booking_date=booking.booking_date,
                amount=refund.amount,
                reference=(
                    f"{'Auszahlung Kundenguthaben' if refund.direction == 'CUSTOMER' else 'Lieferantenerstattung'} · "
                    f"{item.partner_name} · {credit_reference} · "
                    f"Hauptbuch {booking.voucher_no or booking.booking_id}"
                ),
                description=(
                    f"Rückerstattung {refund.amount:.2f} EUR; tatsächliches "
                    f"Zahlungs-/Erstattungsdatum {refund.refund_date:%d.%m.%Y}"
                ),
                booking_id=refund.booking_id,
                recorded_at=refund.recorded_at,
            )
            for refund, booking in refund_rows
        )
        reversal_rows = (
            self._session.query(
                GuthabenOPRueckerstattungsruecknahme,
                GuthabenOPRueckerstattung,
                Buchung,
            )
            .join(
                GuthabenOPRueckerstattung,
                GuthabenOPRueckerstattungsruecknahme.refund_id
                == GuthabenOPRueckerstattung.refund_id,
            )
            .join(
                Buchung,
                GuthabenOPRueckerstattungsruecknahme.reversal_booking_id
                == Buchung.booking_id,
            )
            .filter(GuthabenOPRueckerstattung.open_item_id == str(item.open_item_id))
            .all()
        )
        activities.extend(
            OpenItemActivity(
                kind=OpenItemActivityKind.REFUND_REVERSAL,
                activity_date=booking.booking_date,
                booking_date=booking.booking_date,
                amount=-refund.amount,
                reference=(
                    f"Rücknahme Guthabenrückerstattung · {item.partner_name} · "
                    f"Rückerstattung {refund.refund_id} · Gegenbuchung "
                    f"{booking.voucher_no or booking.booking_id}"
                ),
                description=(
                    f"Guthabenrückerstattung vom {refund.refund_date:%d.%m.%Y} "
                    f"über {refund.amount:.2f} EUR zurückgenommen; "
                    f"Grund: {reversal.reason}"
                ),
                booking_id=reversal.reversal_booking_id,
                recorded_at=reversal.recorded_at,
            )
            for reversal, refund, booking in reversal_rows
        )
        return activities

    def _credit_refund_amount(self, open_item_id: str) -> Decimal:
        refunded = (
            self._session.query(func.sum(GuthabenOPRueckerstattung.amount))
            .filter(GuthabenOPRueckerstattung.open_item_id == str(open_item_id))
            .scalar()
            or ZERO
        )
        returned = (
            self._session.query(func.sum(GuthabenOPRueckerstattung.amount))
            .join(
                GuthabenOPRueckerstattungsruecknahme,
                GuthabenOPRueckerstattungsruecknahme.refund_id
                == GuthabenOPRueckerstattung.refund_id,
            )
            .filter(GuthabenOPRueckerstattung.open_item_id == str(open_item_id))
            .scalar()
            or ZERO
        )
        return refunded - returned

    def _credit_note_number(self, open_item_id: str) -> str:
        number = (
            self._session.query(Gutschrift.note_number)
            .join(GuthabenOP, Gutschrift.credit_note_id == GuthabenOP.credit_note_id)
            .filter(GuthabenOP.open_item_id == open_item_id)
            .scalar()
        )
        return number or "(Gutschriftnummer nicht vorhanden)"

    def _invoice_number_for_open_item(
        self,
        open_item_id: str | None,
        *,
        receivable: bool,
    ) -> str:
        if open_item_id is None:
            return "(Rechnungsnummer nicht vorhanden)"
        if receivable:
            number = (
                self._session.query(Ausgangsrechnung.invoice_number)
                .join(
                    ForderungsOP,
                    Ausgangsrechnung.invoice_id == ForderungsOP.invoice_id,
                )
                .filter(ForderungsOP.open_item_id == open_item_id)
                .scalar()
            )
        else:
            number = (
                self._session.query(Eingangsrechnung.invoice_number)
                .join(
                    VerbindlichkeitsOP,
                    Eingangsrechnung.invoice_id == VerbindlichkeitsOP.invoice_id,
                )
                .filter(VerbindlichkeitsOP.open_item_id == open_item_id)
                .scalar()
            )
        return number or "(Rechnungsnummer nicht vorhanden)"

    def _company(self, company_id: UUID) -> Mandant:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")
        return company

    def _partner_name(self, mandant_id: int, partner_id: str) -> str:
        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == mandant_id,
                Geschaeftspartner.partner_id == partner_id,
            )
            .one_or_none()
        )
        if partner is None:
            raise ValueError("Der OP verweist auf keinen Geschäftspartner.")
        return partner.name
