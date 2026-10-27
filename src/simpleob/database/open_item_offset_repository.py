"""Persistenz und Restbetragsprüfung für manuelle OP-Verrechnungen."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Buchungszeile,
    Eingangsrechnung,
    ForderungsOP,
    Geschaeftspartner,
    GuthabenOP,
    GuthabenOPEreignis,
    Gutschrift,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_offset import (
    CreditOffsetSummary,
    InvoiceOffsetSummary,
    OffsetDirection,
    OpenItemOffset,
)
from simpleob.domain.open_item_payment import PaymentDirection


class OpenItemOffsetRepository:
    """Speichert einen Verrechnungsvorgang und seine beiden OP-Ereignisse."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._payment_repository = OpenItemPaymentRepository(session)

    def get_invoice(
        self,
        *,
        company_id: UUID,
        open_item_id: UUID,
        partner_id: UUID,
        direction: OffsetDirection,
        for_update: bool = False,
    ) -> InvoiceOffsetSummary | None:
        if not isinstance(direction, OffsetDirection):
            raise TypeError("direction must be an OffsetDirection")
        payment_direction = self._payment_direction(direction)
        invoice_summary = self._payment_repository.get_open_invoice(
            company_id=company_id,
            open_item_id=open_item_id,
            direction=payment_direction,
            for_update=for_update,
        )
        if invoice_summary is None:
            return None
        if invoice_summary.partner_id != partner_id:
            raise ValueError("Der Rechnungs-OP gehört zu einem anderen Geschäftspartner.")
        company = self._company(company_id)
        invoice_model = (
            Ausgangsrechnung
            if direction is OffsetDirection.CUSTOMER
            else Eingangsrechnung
        )
        open_item_model = (
            ForderungsOP
            if direction is OffsetDirection.CUSTOMER
            else VerbindlichkeitsOP
        )
        open_item = (
            self._session.query(open_item_model)
            .filter(open_item_model.open_item_id == str(open_item_id))
            .one()
        )
        invoice = (
            self._session.query(invoice_model)
            .filter(invoice_model.invoice_id == open_item.invoice_id)
            .one()
        )
        account_number = self._source_account_number(
            mandant_id=company.id,
            booking_id=invoice.booking_id,
            side=(
                EntrySide.DEBIT
                if direction is OffsetDirection.CUSTOMER
                else EntrySide.CREDIT
            ),
            account_type=(
                AccountType.ASSET
                if direction is OffsetDirection.CUSTOMER
                else AccountType.LIABILITY
            ),
            expected_amount=open_item.amount,
            label="Rechnungs-OP",
        )
        return InvoiceOffsetSummary(
            company_id=company_id,
            partner_id=partner_id,
            open_item_id=open_item_id,
            direction=direction,
            document_number=invoice.invoice_number,
            original_amount=open_item.amount,
            open_amount=invoice_summary.open_amount,
            account_number=account_number,
        )

    def get_credit(
        self,
        *,
        company_id: UUID,
        open_item_id: UUID,
        partner_id: UUID,
        direction: OffsetDirection,
        for_update: bool = False,
    ) -> CreditOffsetSummary | None:
        if not isinstance(direction, OffsetDirection):
            raise TypeError("direction must be an OffsetDirection")
        query = self._session.query(GuthabenOP).filter(
            GuthabenOP.open_item_id == str(open_item_id)
        )
        if for_update:
            query = query.with_for_update()
        open_item = query.one_or_none()
        if open_item is None:
            return None
        credit_note = (
            self._session.query(Gutschrift)
            .filter(Gutschrift.credit_note_id == open_item.credit_note_id)
            .one()
        )
        company = self._session.query(Mandant).filter(
            Mandant.id == credit_note.mandant_id
        ).one()
        if company.company_id != str(company_id):
            raise ValueError("Der Guthaben-OP gehört nicht zum geöffneten Mandanten.")
        expected_kind = direction.value
        if credit_note.credit_note_kind != expected_kind:
            raise ValueError("Guthaben und Rechnungs-OP passen fachlich nicht zusammen.")
        if credit_note.partner_id != str(partner_id):
            raise ValueError("Der Guthaben-OP gehört zu einem anderen Geschäftspartner.")
        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(partner_id),
            )
            .one_or_none()
        )
        partner_role = (
            partner.is_customer
            if partner is not None and direction is OffsetDirection.CUSTOMER
            else partner.is_supplier
            if partner is not None
            else False
        )
        if not partner_role:
            raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")
        event_total = (
            self._session.query(func.sum(GuthabenOPEreignis.amount_delta))
            .filter(GuthabenOPEreignis.open_item_id == str(open_item_id))
            .scalar()
        )
        available_amount = open_item.amount + (event_total or ZERO)
        if available_amount < ZERO:
            raise ValueError("Die Guthaben-OP-Ereignisse reduzieren den Ursprungsbetrag unter null.")
        account_number = self._source_account_number(
            mandant_id=company.id,
            booking_id=credit_note.booking_id,
            side=(
                EntrySide.CREDIT
                if direction is OffsetDirection.CUSTOMER
                else EntrySide.DEBIT
            ),
            account_type=(
                AccountType.LIABILITY
                if direction is OffsetDirection.CUSTOMER
                else AccountType.ASSET
            ),
            expected_amount=open_item.amount,
            label="Guthaben-OP",
        )
        return CreditOffsetSummary(
            company_id=company_id,
            partner_id=partner_id,
            open_item_id=open_item_id,
            direction=direction,
            document_number=credit_note.note_number,
            original_amount=open_item.amount,
            available_amount=available_amount,
            account_number=account_number,
        )

    def list_open_invoices(
        self, *, company_id: UUID, partner_id: UUID, direction: OffsetDirection
    ) -> tuple[InvoiceOffsetSummary, ...]:
        payment_direction = self._payment_direction(direction)
        summaries = []
        for invoice in self._payment_repository.list_open_invoices(company_id):
            if invoice.partner_id == partner_id and invoice.direction is payment_direction:
                summary = self.get_invoice(
                    company_id=company_id,
                    partner_id=partner_id,
                    open_item_id=invoice.open_item_id,
                    direction=direction,
                )
                if summary is not None and summary.open_amount > ZERO:
                    summaries.append(summary)
        return tuple(summaries)

    def list_open_credits(
        self, *, company_id: UUID, partner_id: UUID, direction: OffsetDirection
    ) -> tuple[CreditOffsetSummary, ...]:
        company = self._company_or_none(company_id)
        if company is None:
            return ()
        open_items = (
            self._session.query(GuthabenOP.open_item_id)
            .join(Gutschrift, GuthabenOP.credit_note_id == Gutschrift.credit_note_id)
            .filter(
                Gutschrift.mandant_id == company.id,
                Gutschrift.partner_id == str(partner_id),
                Gutschrift.credit_note_kind == direction.value,
            )
            .all()
        )
        summaries = []
        for (stored_open_item_id,) in open_items:
            summary = self.get_credit(
                company_id=company_id,
                partner_id=partner_id,
                open_item_id=UUID(stored_open_item_id),
                direction=direction,
            )
            if summary is not None and summary.available_amount > ZERO:
                summaries.append(summary)
        return tuple(summaries)

    def add(
        self,
        *,
        offset: OpenItemOffset,
        fiscal_year: FiscalYear,
        commit: bool = True,
    ) -> None:
        if not isinstance(offset, OpenItemOffset):
            raise TypeError("offset must be an OpenItemOffset")
        company = self._company(offset.company_id)
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
        if self._session.query(OPGuthabenverrechnung.id).filter(
            OPGuthabenverrechnung.settlement_id == str(offset.settlement_id)
        ).first():
            raise ValueError("Die Verrechnungs-ID ist bereits vorhanden.")
        if self._session.query(OPGuthabenverrechnung.id).filter(
            OPGuthabenverrechnung.booking_id == str(offset.booking_id)
        ).first():
            raise ValueError("Für diese Hauptbuchbuchung existiert bereits eine Verrechnung.")

        invoice = self.get_invoice(
            company_id=offset.company_id,
            partner_id=offset.partner_id,
            open_item_id=offset.invoice_open_item_id,
            direction=offset.direction,
            for_update=True,
        )
        credit = self.get_credit(
            company_id=offset.company_id,
            partner_id=offset.partner_id,
            open_item_id=offset.credit_open_item_id,
            direction=offset.direction,
            for_update=True,
        )
        if invoice is None or credit is None:
            raise ValueError("Ein zu verrechnender OP ist nicht vorhanden.")
        self.ensure_invoice_not_cancelled(
            open_item_id=offset.invoice_open_item_id,
            direction=self._payment_direction(offset.direction),
        )
        if offset.amount > invoice.open_amount:
            raise ValueError("Der Verrechnungsbetrag übersteigt den offenen Rechnungsbetrag.")
        if offset.amount > credit.available_amount:
            raise ValueError("Der Verrechnungsbetrag übersteigt das verfügbare Guthaben.")
        booking_exists = (
            self._session.query(Buchung.id)
            .filter(
                Buchung.booking_id == str(offset.booking_id),
                Buchung.wirtschaftsjahr_id == fiscal_year_model.id,
            )
            .one_or_none()
        )
        if booking_exists is None:
            raise ValueError("Die Hauptbuchbuchung fehlt oder gehört zu einem anderen Geschäftsjahr.")
        partner_role = (
            Geschaeftspartner.is_customer
            if offset.direction is OffsetDirection.CUSTOMER
            else Geschaeftspartner.is_supplier
        )
        if not self._session.query(Geschaeftspartner.id).filter(
            Geschaeftspartner.mandant_id == company.id,
            Geschaeftspartner.partner_id == str(offset.partner_id),
            partner_role.is_(True),
        ).one_or_none():
            raise ValueError("Der Geschäftspartner gehört nicht zum Mandanten oder hat nicht die passende Rolle.")

        self._session.add(
            OPGuthabenverrechnung(
                settlement_id=str(offset.settlement_id),
                mandant_id=company.id,
                partner_id=str(offset.partner_id),
                direction=offset.direction.value,
                receivable_open_item_id=(
                    str(offset.invoice_open_item_id)
                    if offset.direction is OffsetDirection.CUSTOMER
                    else None
                ),
                payable_open_item_id=(
                    str(offset.invoice_open_item_id)
                    if offset.direction is OffsetDirection.SUPPLIER
                    else None
                ),
                credit_open_item_id=str(offset.credit_open_item_id),
                amount=offset.amount,
                settlement_date=offset.settlement_date,
                recorded_at=offset.recorded_at,
                booking_id=str(offset.booking_id),
            )
        )
        self._session.flush()
        self._session.add_all(
            (
                RechnungsOPVerrechnungsereignis(
                    event_id=str(offset.invoice_event_id),
                    settlement_id=str(offset.settlement_id),
                    direction=offset.direction.value,
                    receivable_open_item_id=(
                        str(offset.invoice_open_item_id)
                        if offset.direction is OffsetDirection.CUSTOMER
                        else None
                    ),
                    payable_open_item_id=(
                        str(offset.invoice_open_item_id)
                        if offset.direction is OffsetDirection.SUPPLIER
                        else None
                    ),
                    amount=offset.amount,
                    effective_date=offset.settlement_date,
                ),
                GuthabenOPEreignis(
                    event_id=str(offset.credit_event_id),
                    settlement_id=str(offset.settlement_id),
                    open_item_id=str(offset.credit_open_item_id),
                    effective_date=offset.settlement_date,
                    amount_delta=-offset.amount,
                ),
            )
        )
        if commit:
            self._session.commit()

    def _source_account_number(
        self,
        *,
        mandant_id: int,
        booking_id: str,
        side: EntrySide,
        account_type: AccountType,
        expected_amount: Decimal,
        label: str,
    ) -> str:
        account_amounts = (
            self._session.query(
                Buchungszeile.account_number,
                func.sum(Buchungszeile.amount),
            )
            .join(Buchung, Buchungszeile.buchung_id == Buchung.id)
            .join(
                Konto,
                (Konto.mandant_id == mandant_id)
                & (Konto.account_number == Buchungszeile.account_number),
            )
            .filter(
                Buchung.booking_id == booking_id,
                Buchungszeile.side == side.value,
                Konto.account_type == account_type.name,
            )
            .group_by(Buchungszeile.account_number)
            .all()
        )
        matches = [
            account_number
            for account_number, total in account_amounts
            if total == expected_amount
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Das tatsächlich bebuchte {label}-Konto ist nicht eindeutig ermittelbar."
            )
        return matches[0]

    def ensure_invoice_not_cancelled(
        self,
        *,
        open_item_id: UUID,
        direction: OffsetDirection,
    ) -> None:
        self._payment_repository.ensure_not_cancelled(
            open_item_id=open_item_id,
            direction=self._payment_direction(direction),
        )

    def _company(self, company_id: UUID) -> Mandant:
        company = self._company_or_none(company_id)
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        return company

    def _company_or_none(self, company_id: UUID) -> Mandant | None:
        return (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )

    @staticmethod
    def _payment_direction(direction: OffsetDirection) -> PaymentDirection:
        return (
            PaymentDirection.CUSTOMER_RECEIPT
            if direction is OffsetDirection.CUSTOMER
            else PaymentDirection.SUPPLIER_PAYMENT
        )
