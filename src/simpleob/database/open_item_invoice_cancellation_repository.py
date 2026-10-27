"""Validierung und atomare Speicherung vollständiger Rechnungs-OP-Stornos."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchungszeile,
    Eingangsrechnung,
    ForderungsOP,
    Geschaeftspartner,
    GuthabenOP,
    Konto,
    Mandant,
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.database.models import Buchung as BuchungModel
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_payment_repository import (
    OpenItemPaymentRepository,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_invoice_cancellation import (
    InvoiceCancellationPaymentAssessment,
    InvoiceCancellationPreview,
)
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_payment import PaymentDirection


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
            allow_payment_history=True,
        )

    def assess_payment_history(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
        proposed_booking_date: date,
    ) -> InvoiceCancellationPaymentAssessment:
        """Prüft die Zahlungszuordnung für eine spätere Stornostufe.

        Diese Methode erzeugt weder eine Stornierung noch eine Buchung. Der
        aktuelle Storno- und Schreibpfad aus 4D-2 bleibt davon getrennt.
        """
        if not isinstance(proposed_booking_date, date):
            raise TypeError("Das vorgesehene Stornobuchungsdatum muss ein Datum sein.")
        company = self._company(company_id)
        target_year = self._booking_repository.require_open_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
            booking_date=proposed_booking_date,
            for_update=False,
        )
        invoice = self._load_eligible_invoice(
            company=company,
            target_year=target_year,
            open_item_id=open_item_id,
            for_update=False,
            allow_payment_history=True,
        )
        direction = (
            PaymentDirection.SUPPLIER_PAYMENT
            if invoice.supplier_invoice
            else PaymentDirection.CUSTOMER_RECEIPT
        )
        payment_event_amount, correction_delta, payment_dates, correction_dates, correction_count = (
            self._payment_history_totals(
                company=company,
                partner_id=invoice.partner_id,
                open_item_id=open_item_id,
                direction=direction,
            )
        )
        effective_payment_amount = payment_event_amount + correction_delta
        original_amount = invoice.amount
        if effective_payment_amount < ZERO or effective_payment_amount > original_amount:
            raise ValueError(
                "Die Zahlungszuordnungshistorie ist widersprüchlich: "
                "wirksame Zahlungen liegen außerhalb des Rechnungsbetrags."
            )
        open_amount = original_amount - effective_payment_amount
        current = OpenItemPaymentRepository(self._session).get_open_invoice(
            company_id=company_id,
            open_item_id=open_item_id,
            direction=direction,
        )
        if current is None or current.open_amount != open_amount:
            raise ValueError(
                "Die Zahlungs- und OP-Historie ist widersprüchlich; "
                "eine spätere Stornierung ist nicht sicher prüfbar."
            )

        latest_payment_date = max(payment_dates, default=None)
        latest_correction_date = max(correction_dates, default=None)
        latest_required_date = max(
            (value for value in (latest_payment_date, latest_correction_date) if value is not None),
            default=None,
        )
        if latest_required_date is not None and proposed_booking_date < latest_required_date:
            raise ValueError(
                "Das Stornobuchungsdatum darf nicht vor dem spätesten "
                "Zahlungs- oder Korrekturbuchungsdatum liegen."
            )
        return InvoiceCancellationPaymentAssessment(
            company_id=invoice.company_id,
            partner_id=invoice.partner_id,
            open_item_id=invoice.open_item_id,
            invoice_number=invoice.invoice_number,
            invoice_amount=original_amount,
            payment_event_amount=payment_event_amount,
            correction_delta=correction_delta,
            effective_payment_amount=effective_payment_amount,
            open_amount=open_amount,
            latest_payment_booking_date=latest_payment_date,
            latest_correction_booking_date=latest_correction_date,
            latest_required_booking_date=latest_required_date,
            payment_event_count=len(payment_dates),
            correction_count=correction_count,
        )

    def _payment_history_totals(
        self,
        *,
        company: Mandant,
        partner_id: UUID,
        open_item_id: UUID,
        direction: PaymentDirection,
    ) -> tuple[Decimal, Decimal, list[date], list[date], int]:
        is_supplier = direction is PaymentDirection.SUPPLIER_PAYMENT
        item_column = (
            RechnungsOPZahlungsereignis.payable_open_item_id
            if is_supplier
            else RechnungsOPZahlungsereignis.receivable_open_item_id
        )
        payment_rows = (
            self._session.query(
                RechnungsOPZahlungsereignis,
                Zahlung,
                BuchungModel,
                Wirtschaftsjahr,
            )
            .join(Zahlung, Zahlung.payment_id == RechnungsOPZahlungsereignis.payment_id)
            .join(BuchungModel, BuchungModel.booking_id == Zahlung.booking_id)
            .join(Wirtschaftsjahr, Wirtschaftsjahr.id == BuchungModel.wirtschaftsjahr_id)
            .filter(item_column == str(open_item_id))
            .all()
        )
        payment_total = ZERO
        payment_dates: list[date] = []
        seen_payment_ids: set[str] = set()
        for event, payment, booking, fiscal_year in payment_rows:
            if (
                event.direction != direction.value
                or payment.direction != direction.value
                or payment.mandant_id != company.id
                or payment.partner_id != str(partner_id)
                or fiscal_year.mandant_id != company.id
            ):
                raise ValueError(
                    "Eine Zahlungszuordnung verweist auf einen unpassenden "
                    "Mandanten, Geschäftspartner oder Zahlungsrichtung."
                )
            payment_total += Decimal(event.amount)
            payment_dates.append(booking.booking_date)
            seen_payment_ids.add(payment.payment_id)

        for payment_id in seen_payment_ids:
            payment = self._session.query(Zahlung).filter_by(payment_id=payment_id).one()
            total_allocated = (
                self._session.query(func.sum(RechnungsOPZahlungsereignis.amount))
                .filter(RechnungsOPZahlungsereignis.payment_id == payment_id)
                .scalar()
            ) or ZERO
            if Decimal(total_allocated) != Decimal(payment.amount):
                raise ValueError(
                    "Die Summe der Zahlungszuordnungen stimmt nicht mit "
                    "dem Zahlungsbetrag überein."
                )

        source_column = (
            Zahlungszuordnungskorrektur.source_payable_open_item_id
            if is_supplier
            else Zahlungszuordnungskorrektur.source_receivable_open_item_id
        )
        target_column = (
            Zahlungszuordnungskorrektur.target_payable_open_item_id
            if is_supplier
            else Zahlungszuordnungskorrektur.target_receivable_open_item_id
        )
        corrections = (
            self._session.query(Zahlungszuordnungskorrektur)
            .filter(
                or_(
                    source_column == str(open_item_id),
                    target_column == str(open_item_id),
                )
            )
            .all()
        )
        correction_delta = ZERO
        correction_dates: list[date] = []
        event_item_column = (
            Zahlungszuordnungskorrekturereignis.payable_open_item_id
            if is_supplier
            else Zahlungszuordnungskorrekturereignis.receivable_open_item_id
        )
        for correction in corrections:
            if (
                correction.mandant_id != company.id
                or correction.partner_id != str(partner_id)
                or correction.direction != direction.value
            ):
                raise ValueError(
                    "Eine Zahlungszuordnungskorrektur verweist auf einen "
                    "unpassenden Mandanten, Geschäftspartner oder Richtung."
                )
            original_payment = (
                self._session.query(Zahlung)
                .filter_by(payment_id=correction.original_payment_id)
                .one_or_none()
            )
            original_event = (
                self._session.query(RechnungsOPZahlungsereignis)
                .filter_by(event_id=correction.original_allocation_event_id)
                .one_or_none()
            )
            if (
                original_payment is None
                or original_event is None
                or original_payment.mandant_id != company.id
                or original_payment.partner_id != str(partner_id)
                or original_payment.direction != direction.value
                or original_event.payment_id != correction.original_payment_id
                or original_event.direction != direction.value
            ):
                raise ValueError(
                    "Die Zahlungszuordnungskorrektur verweist nicht auf "
                    "ihre passende ursprüngliche Zahlung."
                )
            if correction.booking_date is None:
                raise ValueError(
                    "Eine zugehörige Zahlungszuordnungskorrektur hat kein "
                    "gespeichertes Buchungsdatum; die Stornierung kann zeitlich "
                    "nicht sicher geprüft werden."
                )
            is_source = (
                getattr(correction, source_column.key) == str(open_item_id)
            )
            expected_role = "SOURCE_RELEASE" if is_source else "TARGET_APPLY"
            expected_delta = -Decimal(correction.amount) if is_source else Decimal(correction.amount)
            matching_events = (
                self._session.query(Zahlungszuordnungskorrekturereignis)
                .filter(
                    Zahlungszuordnungskorrekturereignis.correction_id
                    == correction.correction_id,
                    event_item_column == str(open_item_id),
                )
                .all()
            )
            if (
                len(matching_events) != 1
                or matching_events[0].event_role != expected_role
                or matching_events[0].direction != direction.value
                or Decimal(matching_events[0].amount_delta) != expected_delta
            ):
                raise ValueError(
                    "Die Zahlungszuordnungskorrektur und ihre OP-Ereignisse "
                    "sind widersprüchlich."
                )
            correction_delta += Decimal(matching_events[0].amount_delta)
            correction_dates.append(correction.booking_date)

        return payment_total, correction_delta, payment_dates, correction_dates, len(corrections)

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
            # OP-Schreibpfade sperren zuerst die betroffenen OP-Zeilen und
            # anschließend das Geschäftsjahr in BookingRepository.add().
            # Dieselbe Reihenfolge verhindert eine FY/OP-Lock-Inversion.
            target_year = self._booking_repository.require_open_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking_date=booking_date,
                for_update=False,
            )
            preview = self._load_eligible_invoice(
                company=company,
                target_year=target_year,
                open_item_id=open_item_id,
                for_update=True,
                allow_payment_history=True,
            )
            locked_year = self._booking_repository.require_open_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking_date=booking_date,
                for_update=True,
            )
            if locked_year.id != target_year.id:
                raise ValueError("Das ausgewählte Geschäftsjahr hat sich während der Prüfung geändert.")
            assessment = self.assess_payment_history(
                company_id=company_id,
                fiscal_year=fiscal_year,
                open_item_id=open_item_id,
                proposed_booking_date=booking_date,
            )
            invoice_amount = preview.amount
            paid_amount = assessment.effective_payment_amount
            open_amount = assessment.open_amount
            if (
                assessment.invoice_amount != invoice_amount
                or paid_amount < ZERO
                or paid_amount > invoice_amount
                or open_amount < ZERO
                or open_amount > invoice_amount
                or open_amount != invoice_amount - paid_amount
            ):
                raise ValueError("Die Zahlungs- und Rechnungsbeträge sind nicht konsistent.")

            transfer_booking: Booking | None = None
            if paid_amount > ZERO:
                transfer_booking = self._build_paid_amount_transfer(
                    company_id=company_id,
                    partner_id=preview.partner_id,
                    open_item_id=preview.open_item_id,
                    supplier_invoice=preview.supplier_invoice,
                    original_booking=preview.original_booking,
                    booking_date=booking_date,
                    amount=paid_amount,
                    invoice_number=preview.invoice_number,
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
            self._session.add(stored_booking)
            self._session.flush()
            if transfer_booking is not None:
                self._booking_repository.add(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    booking=transfer_booking,
                    commit=False,
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
                amount=invoice_amount,
                closed_open_amount=open_amount,
                credit_booking_id=(
                    str(transfer_booking.booking_id)
                    if transfer_booking is not None
                    else None
                ),
                recorded_at=datetime.now(timezone.utc),
                reason=reason,
            )
            self._session.add(storno)
            self._session.flush()
            if transfer_booking is not None:
                self._session.add(
                    GuthabenOP(
                        open_item_id=str(uuid4()),
                        credit_note_id=None,
                        invoice_cancellation_id=storno.storno_id,
                        amount=paid_amount,
                    )
                )
                self._session.flush()
            self._booking_repository.commit()
            return UUID(storno.storno_id)
        except Exception:
            self._booking_repository.rollback()
            raise

    def _build_paid_amount_transfer(
        self,
        *,
        company_id: UUID,
        partner_id: UUID,
        open_item_id: UUID,
        supplier_invoice: bool,
        original_booking: Booking,
        booking_date: date,
        amount: Decimal,
        invoice_number: str,
    ) -> Booking:
        chart = ChartOfAccountsRepository(self._session)
        roles = chart.load_account_roles(company_id)
        if roles is None:
            raise ValueError("Für den Mandanten sind keine Kontenrollen konfiguriert.")
        credit_accounts = (
            roles.supplier_credit_balances
            if supplier_invoice
            else roles.customer_credit_balances
        )
        role_label = "Lieferantenguthabenkonto" if supplier_invoice else "Kundenguthabenkonto"
        if len(credit_accounts) != 1:
            raise ValueError(f"Für den Mandanten muss genau ein {role_label} konfiguriert sein.")
        credit_account = next(iter(credit_accounts))
        validator = (
            chart.validate_supplier_credit_balance_account
            if supplier_invoice
            else chart.validate_customer_credit_balance_account
        )
        validator(company_id=company_id, account_number=credit_account)

        direction = OffsetDirection.SUPPLIER if supplier_invoice else OffsetDirection.CUSTOMER
        invoice = OpenItemOffsetRepository(self._session).get_invoice(
            company_id=company_id,
            partner_id=partner_id,
            open_item_id=open_item_id,
            direction=direction,
            for_update=True,
        )
        if invoice is None:
            raise ValueError("Das Forderungs- beziehungsweise Verbindlichkeitskonto der Rechnung ist nicht ermittelbar.")
        if invoice.account_number not in {line.account_number for line in original_booking.lines}:
            raise ValueError("Das tatsächliche Rechnungskonto stimmt nicht mit der Originalbuchung überein.")

        if supplier_invoice:
            lines = (
                BookingLine(credit_account, EntrySide.DEBIT, amount),
                BookingLine(invoice.account_number, EntrySide.CREDIT, amount),
            )
        else:
            lines = (
                BookingLine(invoice.account_number, EntrySide.DEBIT, amount),
                BookingLine(credit_account, EntrySide.CREDIT, amount),
            )
        return Booking(
            booking_date=booking_date,
            description=f"Guthabenübertrag aus Rechnungsstorno {invoice_number}",
            lines=lines,
        )

    def _load_eligible_invoice(
        self,
        *,
        company: Mandant,
        target_year: Wirtschaftsjahr,
        open_item_id: UUID,
        for_update: bool,
        allow_payment_history: bool = False,
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

        if allow_payment_history:
            self._ensure_no_offset_history(
                open_item_id=open_item_id,
                supplier_invoice=supplier_invoice,
            )
        else:
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
        if self._session.query(RechnungsOPZahlungsereignis.id).filter(
            payment_column == str(open_item_id)
        ).first():
            raise ValueError("Die Rechnung hat Zahlungshistorie und kann in dieser Stufe nicht storniert werden.")
        self._ensure_no_offset_history(
            open_item_id=open_item_id,
            supplier_invoice=supplier_invoice,
        )
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

    def _ensure_no_offset_history(
        self,
        *,
        open_item_id: UUID,
        supplier_invoice: bool,
    ) -> None:
        offset_column = (
            RechnungsOPVerrechnungsereignis.payable_open_item_id
            if supplier_invoice
            else RechnungsOPVerrechnungsereignis.receivable_open_item_id
        )
        if self._session.query(RechnungsOPVerrechnungsereignis.id).filter(
            offset_column == str(open_item_id)
        ).first():
            raise ValueError("Die Rechnung hat Verrechnungshistorie und kann in dieser Stufe nicht storniert werden.")

    def _company(self, company_id: UUID) -> Mandant:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        company = self._session.query(Mandant).filter_by(
            company_id=str(company_id)
        ).one_or_none()
        if company is None:
            raise ValueError("Der Mandant wurde nicht gefunden.")
        return company
