"""Validierung und atomare Speicherung vollständiger Rechnungs-OP-Stornos."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchungszeile,
    Eingangsrechnung,
    ForderungsOP,
    Geschaeftspartner,
    Konto,
    Mandant,
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.database.models import (
    Buchung as BuchungModel,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_invoice_cancellation import (
    InvoiceCancellationPreview,
)


class OpenItemInvoiceCancellationRepository:
    """Persistiert nur geprüfte und vollständige OP-Rechnungsstornos."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository

    def preview(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
    ) -> InvoiceCancellationPreview:
        company = self._company(company_id)
        target_year = self._booking_repository.require_open_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
            booking_date=fiscal_year.start_date,
            for_update=False,
        )
        return self._load_eligible_invoice(
            company=company,
            target_year=target_year,
            open_item_id=open_item_id,
            for_update=False,
        )

    def add_atomic(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
        booking_date: date,
        reason: str,
    ) -> UUID:
        try:
            if not isinstance(booking_date, date):
                raise TypeError("Das Stornobuchungsdatum muss ein Datum sein.")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Bitte geben Sie einen Stornogrund ein.")
            reason = reason.strip()
            company = self._company(company_id)
            target_year = self._booking_repository.require_open_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking_date=booking_date,
                for_update=True,
            )
            preview = self._load_eligible_invoice(
                company=company,
                target_year=target_year,
                open_item_id=open_item_id,
                for_update=True,
            )
            reversal = Booking(
                booking_date=booking_date,
                description=(
                    f"Storno zu Rechnung {preview.invoice_number}"
                ),
                booking_type=BookingType.REVERSAL,
                reversal_of_booking_id=preview.original_booking.booking_id,
                lines=tuple(
                    BookingLine(
                        account_number=line.account_number,
                        side=(
                            EntrySide.CREDIT
                            if line.side is EntrySide.DEBIT
                            else EntrySide.DEBIT
                        ),
                        amount=line.amount,
                    )
                    for line in preview.original_booking.lines
                ),
            )
            stored_booking = BuchungModel(
                booking_id=str(reversal.booking_id),
                wirtschaftsjahr_id=target_year.id,
                booking_date=reversal.booking_date,
                voucher_no=None,
                description=(
                    f"{reversal.description}: {reason}"
                ),
                booking_type=reversal.booking_type.value,
                reversal_of_booking_id=str(
                    preview.original_booking.booking_id
                ),
                zeilen=[
                    Buchungszeile(
                        position=position,
                        account_number=line.account_number,
                        side=line.side.value,
                        amount=line.amount,
                    )
                    for position, line in enumerate(reversal.lines)
                ],
            )
            storno = RechnungsOPStorno(
                storno_id=str(uuid4()),
                mandant_id=company.id,
                partner_id=str(preview.partner_id),
                receivable_invoice_id=(
                    str(preview.invoice_id)
                    if not preview.supplier_invoice
                    else None
                ),
                payable_invoice_id=(
                    str(preview.invoice_id)
                    if preview.supplier_invoice
                    else None
                ),
                receivable_open_item_id=(
                    str(preview.open_item_id)
                    if not preview.supplier_invoice
                    else None
                ),
                payable_open_item_id=(
                    str(preview.open_item_id)
                    if preview.supplier_invoice
                    else None
                ),
                booking_id=str(reversal.booking_id),
                amount=preview.amount,
                closed_open_amount=preview.amount,
                recorded_at=datetime.now(timezone.utc),
                reason=reason,
            )
            self._session.add_all((stored_booking, storno))
            self._session.flush()
            self._booking_repository.commit()
            return UUID(storno.storno_id)
        except Exception:
            self._booking_repository.rollback()
            raise

    def _load_eligible_invoice(
        self,
        *,
        company: Mandant,
        target_year: Wirtschaftsjahr,
        open_item_id: UUID,
        for_update: bool,
    ) -> InvoiceCancellationPreview:
        receivable_query = self._session.query(ForderungsOP).filter(
            ForderungsOP.open_item_id == str(open_item_id)
        )
        payable_query = self._session.query(VerbindlichkeitsOP).filter(
            VerbindlichkeitsOP.open_item_id == str(open_item_id)
        )
        if for_update and self._session.get_bind().dialect.name == "postgresql":
            receivable_query = receivable_query.with_for_update()
            payable_query = payable_query.with_for_update()
        receivable_op = receivable_query.one_or_none()
        payable_op = payable_query.one_or_none()
        if (receivable_op is None) == (payable_op is None):
            raise ValueError("Der Rechnungs-OP fehlt oder ist nicht eindeutig.")

        supplier_invoice = payable_op is not None
        open_item = payable_op if supplier_invoice else receivable_op
        invoice_model = Eingangsrechnung if supplier_invoice else Ausgangsrechnung
        invoice = (
            self._session.query(invoice_model)
            .filter(invoice_model.invoice_id == open_item.invoice_id)
            .one_or_none()
        )
        if invoice is None or invoice.mandant_id != company.id:
            raise ValueError("Die Rechnung gehört nicht zum geöffneten Mandanten.")
        if Decimal(open_item.amount) != Decimal(invoice.gross_amount):
            raise ValueError("Rechnungsbetrag und OP-Ursprungsbetrag stimmen nicht überein.")
        if open_item.amount <= ZERO:
            raise ValueError("Der Rechnungs-OP hat keinen positiven Ursprungsbetrag.")

        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == invoice.partner_id,
            )
            .one_or_none()
        )
        if partner is None or not (
            partner.is_supplier if supplier_invoice else partner.is_customer
        ):
            raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")

        original_model = (
            self._session.query(BuchungModel)
            .join(Wirtschaftsjahr, BuchungModel.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                BuchungModel.booking_id == invoice.booking_id,
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .one_or_none()
        )
        if original_model is None:
            raise ValueError("Die Originalbuchung fehlt oder gehört zu einem anderen Mandanten.")
        if original_model.booking_type != BookingType.REGULAR.value:
            raise ValueError("Nur eine reguläre Originalbuchung kann storniert werden.")
        source_year = (
            self._session.query(Wirtschaftsjahr)
            .filter(Wirtschaftsjahr.id == original_model.wirtschaftsjahr_id)
            .one()
        )
        if (
            source_year.start_date != target_year.start_date
            or source_year.end_date != target_year.end_date
            or not (
                source_year.start_date
                <= original_model.booking_date
                <= source_year.end_date
            )
        ):
            raise ValueError(
                "Die Originalrechnung muss im ausgewählten Geschäftsjahr gebucht sein."
            )
        if self._session.query(BuchungModel.id).filter(
            BuchungModel.reversal_of_booking_id == str(original_model.booking_id)
        ).first():
            raise ValueError("Für diese Rechnungsbuchung existiert bereits eine Gegenbuchung.")

        storno_query = self._session.query(RechnungsOPStorno.id)
        if supplier_invoice:
            storno_query = storno_query.filter(
                RechnungsOPStorno.payable_invoice_id == invoice.invoice_id
            )
        else:
            storno_query = storno_query.filter(
                RechnungsOPStorno.receivable_invoice_id == invoice.invoice_id
            )
        if storno_query.first():
            raise ValueError("Die Rechnung wurde bereits storniert.")

        self._ensure_no_history(
            open_item_id=open_item_id,
            supplier_invoice=supplier_invoice,
        )

        booking_lines = tuple(
            BookingLine(
                account_number=line.account_number,
                side=EntrySide.from_value(line.side),
                amount=Decimal(line.amount),
            )
            for line in sorted(original_model.zeilen, key=lambda row: row.position)
        )
        if len(booking_lines) < 2:
            raise ValueError("Die Originalbuchung enthält nicht alle Buchungszeilen.")
        debit_total = sum(
            (line.amount for line in booking_lines if line.side is EntrySide.DEBIT),
            start=ZERO,
        )
        credit_total = sum(
            (line.amount for line in booking_lines if line.side is EntrySide.CREDIT),
            start=ZERO,
        )
        if debit_total != credit_total:
            raise ValueError("Die Originalbuchung ist nicht ausgeglichen.")
        account_numbers = {line.account_number for line in booking_lines}
        tenant_accounts = {
            number
            for (number,) in self._session.query(Konto.account_number)
            .filter(
                Konto.mandant_id == company.id,
                Konto.account_number.in_(account_numbers),
            )
            .all()
        }
        if tenant_accounts != account_numbers:
            raise ValueError("Mindestens ein Buchungskonto gehört nicht zum Mandanten.")

        original_booking = Booking(
            booking_id=UUID(original_model.booking_id),
            booking_date=original_model.booking_date,
            voucher_no=original_model.voucher_no,
            description=original_model.description,
            booking_type=BookingType(original_model.booking_type),
            lines=booking_lines,
        )
        return InvoiceCancellationPreview(
            company_id=UUID(company.company_id),
            partner_id=UUID(invoice.partner_id),
            partner_name=partner.name,
            invoice_id=UUID(invoice.invoice_id),
            open_item_id=UUID(open_item.open_item_id),
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            invoice_booking_date=original_model.booking_date,
            amount=Decimal(open_item.amount),
            original_booking=original_booking,
            supplier_invoice=supplier_invoice,
        )

    def _ensure_no_history(
        self,
        *,
        open_item_id: UUID,
        supplier_invoice: bool,
    ) -> None:
        payment_column = (
            RechnungsOPZahlungsereignis.payable_open_item_id
            if supplier_invoice
            else RechnungsOPZahlungsereignis.receivable_open_item_id
        )
        offset_column = (
            RechnungsOPVerrechnungsereignis.payable_open_item_id
            if supplier_invoice
            else RechnungsOPVerrechnungsereignis.receivable_open_item_id
        )
        if self._session.query(RechnungsOPZahlungsereignis.id).filter(
            payment_column == str(open_item_id)
        ).first():
            raise ValueError("Die Rechnung hat Zahlungshistorie und kann in dieser Stufe nicht storniert werden.")
        if self._session.query(RechnungsOPVerrechnungsereignis.id).filter(
            offset_column == str(open_item_id)
        ).first():
            raise ValueError("Die Rechnung hat Verrechnungshistorie und kann in dieser Stufe nicht storniert werden.")
        source_column = (
            Zahlungszuordnungskorrektur.source_payable_open_item_id
            if supplier_invoice
            else Zahlungszuordnungskorrektur.source_receivable_open_item_id
        )
        target_column = (
            Zahlungszuordnungskorrektur.target_payable_open_item_id
            if supplier_invoice
            else Zahlungszuordnungskorrektur.target_receivable_open_item_id
        )
        if self._session.query(Zahlungszuordnungskorrektur.correction_id).filter(
            or_(
                source_column == str(open_item_id),
                target_column == str(open_item_id),
            )
        ).first():
            raise ValueError("Die Rechnung hat Korrekturhistorie und kann in dieser Stufe nicht storniert werden.")
        correction_event_column = (
            Zahlungszuordnungskorrekturereignis.payable_open_item_id
            if supplier_invoice
            else Zahlungszuordnungskorrekturereignis.receivable_open_item_id
        )
        if self._session.query(Zahlungszuordnungskorrekturereignis.id).filter(
            correction_event_column == str(open_item_id)
        ).first():
            raise ValueError("Die Rechnung hat Korrekturhistorie und kann in dieser Stufe nicht storniert werden.")

    def _company(self, company_id: UUID) -> Mandant:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        company = self._session.query(Mandant).filter_by(
            company_id=str(company_id)
        ).one_or_none()
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")
        return company
