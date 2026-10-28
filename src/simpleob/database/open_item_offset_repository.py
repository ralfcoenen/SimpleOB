"""Persistenz und Restbetragsprüfung für manuelle OP-Verrechnungen."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from simpleob.database.lock_error import DatabaseLockError
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
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.database.open_item_credit_balance import available_credit_amount
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
        cancellation_booking_date = None
        origin_booking_date = None
        if open_item.credit_note_id is not None:
            credit_note = (
                self._session.query(Gutschrift)
                .filter(Gutschrift.credit_note_id == open_item.credit_note_id)
                .one_or_none()
            )
            if credit_note is None:
                raise ValueError("Die Gutschrift-Herkunft des Guthaben-OPs fehlt.")
            company = self._session.query(Mandant).filter(
                Mandant.id == credit_note.mandant_id
            ).one()
            if credit_note.credit_note_kind != direction.value:
                raise ValueError("Guthaben und Rechnungs-OP passen fachlich nicht zusammen.")
            if credit_note.partner_id != str(partner_id):
                raise ValueError("Der Guthaben-OP gehört zu einem anderen Geschäftspartner.")
            source_booking_id = credit_note.booking_id
            document_number = credit_note.note_number
        elif open_item.invoice_cancellation_id is not None:
            cancellation = (
                self._session.query(RechnungsOPStorno)
                .filter(RechnungsOPStorno.storno_id == open_item.invoice_cancellation_id)
                .one_or_none()
            )
            if cancellation is None or cancellation.credit_booking_id is None:
                raise ValueError("Die Stornoherkunft oder Guthabenumbuchung des Guthaben-OPs fehlt.")
            company = self._session.query(Mandant).filter(
                Mandant.id == cancellation.mandant_id
            ).one()
            if cancellation.partner_id != str(partner_id):
                raise ValueError("Der Guthaben-OP gehört zu einem anderen Geschäftspartner.")
            if direction is OffsetDirection.CUSTOMER:
                if cancellation.receivable_invoice_id is None or cancellation.payable_invoice_id is not None:
                    raise ValueError("Die Stornoherkunft passt nicht zu einem Kundenguthaben.")
                source_invoice = (
                    self._session.query(Ausgangsrechnung)
                    .filter(Ausgangsrechnung.invoice_id == cancellation.receivable_invoice_id)
                    .one_or_none()
                )
            else:
                if cancellation.payable_invoice_id is None or cancellation.receivable_invoice_id is not None:
                    raise ValueError("Die Stornoherkunft passt nicht zu einem Lieferantenguthaben.")
                source_invoice = (
                    self._session.query(Eingangsrechnung)
                    .filter(Eingangsrechnung.invoice_id == cancellation.payable_invoice_id)
                    .one_or_none()
                )
            if (
                source_invoice is None
                or source_invoice.mandant_id != company.id
                or source_invoice.partner_id != cancellation.partner_id
            ):
                raise ValueError("Rechnungsstorno und Guthaben-OP haben keine passende Mandanten-/Partnerherkunft.")
            source_booking_id = cancellation.credit_booking_id
            document_number = f"Storno {source_invoice.invoice_number}"
            referenced_bookings = (
                self._session.query(Buchung, Wirtschaftsjahr)
                .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
                .filter(
                    Buchung.booking_id.in_(
                        (cancellation.booking_id, source_booking_id)
                    ),
                )
                .all()
            )
            bookings_by_id = {
                booking.booking_id: (booking, fiscal_year)
                for booking, fiscal_year in referenced_bookings
            }
            reversal_reference = bookings_by_id.get(cancellation.booking_id)
            transfer_reference = bookings_by_id.get(source_booking_id)
            if reversal_reference is None or transfer_reference is None:
                raise ValueError(
                    "Die Rechnungsgegenbuchung oder Guthabenumbuchung fehlt."
                )
            reversal_booking, reversal_year = reversal_reference
            transfer_booking, transfer_year = transfer_reference
            if (
                reversal_year.mandant_id != company.id
                or transfer_year.mandant_id != company.id
            ):
                raise ValueError(
                    "Die Rechnungsgegenbuchung oder Guthabenumbuchung "
                    "gehört zu einem anderen Mandanten."
                )
            if (
                reversal_booking.wirtschaftsjahr_id
                != transfer_booking.wirtschaftsjahr_id
                or reversal_booking.booking_date != transfer_booking.booking_date
            ):
                raise ValueError(
                    "Rechnungsgegenbuchung und Guthabenumbuchung müssen "
                    "dasselbe Geschäftsjahr und Buchungsdatum haben."
                )
            cancellation_booking_date = transfer_booking.booking_date
            origin_booking_date = transfer_booking.booking_date
        else:
            raise ValueError("Der Guthaben-OP hat keine unterstützte Herkunft.")
        if company.company_id != str(company_id):
            raise ValueError("Der Guthaben-OP gehört nicht zum geöffneten Mandanten.")
        if origin_booking_date is None:
            source_booking = (
                self._session.query(Buchung, Wirtschaftsjahr)
                .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
                .filter(
                    Buchung.booking_id == source_booking_id,
                    Wirtschaftsjahr.mandant_id == company.id,
                )
                .one_or_none()
            )
            if source_booking is None:
                raise ValueError("Die Buchung zur Guthabenentstehung fehlt oder gehört zu einem anderen Mandanten.")
            source_booking_model, _source_year = source_booking
            origin_booking_date = source_booking_model.booking_date
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
        available_amount = available_credit_amount(
            self._session,
            open_item_id=open_item_id,
            original_amount=open_item.amount,
        )
        account_number = self._source_account_number(
            mandant_id=company.id,
            booking_id=source_booking_id,
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
            document_number=document_number,
            original_amount=open_item.amount,
            available_amount=available_amount,
            account_number=account_number,
            cancellation_booking_date=cancellation_booking_date,
            origin_booking_date=origin_booking_date,
        )

    def reserve_credit_mutation(self) -> None:
        """Reserviert unter SQLite Schreibzugriff vor OP-Leseprüfungen."""
        connection = self._session.connection()
        if connection.dialect.name != "sqlite":
            return
        driver_connection = connection.connection.driver_connection
        transaction = self._session.get_transaction()
        if self._session.info.get("_sqlite_credit_mutation_transaction") is transaction:
            return
        if driver_connection.in_transaction:
            raise DatabaseLockError(
                "Die SQLite-Sitzung hat bereits eine Datenbanktransaktion begonnen. "
                "Die Guthabenänderung wurde abgebrochen; bitte erneut versuchen."
            )
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        except OperationalError as exc:
            raise DatabaseLockError(
                "Das Guthaben wird gerade durch einen anderen Vorgang geändert. "
                "Es wurden keine Änderungen gespeichert; bitte erneut versuchen."
            ) from exc
        self._session.info["_sqlite_credit_mutation_transaction"] = transaction

    @staticmethod
    def ensure_credit_booking_date(
        *, credit: CreditOffsetSummary, booking_date: date
    ) -> None:
        """Verhindert eine Verrechnung vor Entstehung eines Storno-Guthabens."""
        if (
            credit.cancellation_booking_date is not None
            and booking_date < credit.cancellation_booking_date
        ):
            raise ValueError(
                "Das Buchungsdatum der Verrechnung darf nicht vor dem "
                "Entstehungsdatum des stornobasierten Guthabens liegen "
                f"({credit.cancellation_booking_date:%d.%m.%Y})."
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
        credit_note_items = (
            self._session.query(GuthabenOP.open_item_id)
            .join(Gutschrift, GuthabenOP.credit_note_id == Gutschrift.credit_note_id)
            .filter(
                Gutschrift.mandant_id == company.id,
                Gutschrift.partner_id == str(partner_id),
                Gutschrift.credit_note_kind == direction.value,
            )
            .all()
        )
        if direction is OffsetDirection.CUSTOMER:
            cancellation_ids = [
                storno_id
                for (storno_id,) in
                self._session.query(RechnungsOPStorno.storno_id)
                .join(
                    Ausgangsrechnung,
                    RechnungsOPStorno.receivable_invoice_id == Ausgangsrechnung.invoice_id,
                )
                .filter(
                    RechnungsOPStorno.mandant_id == company.id,
                    RechnungsOPStorno.partner_id == str(partner_id),
                    Ausgangsrechnung.mandant_id == company.id,
                    Ausgangsrechnung.partner_id == str(partner_id),
                    RechnungsOPStorno.credit_booking_id.is_not(None),
                ).all()
            ]
        else:
            cancellation_ids = [
                storno_id
                for (storno_id,) in
                self._session.query(RechnungsOPStorno.storno_id)
                .join(
                    Eingangsrechnung,
                    RechnungsOPStorno.payable_invoice_id == Eingangsrechnung.invoice_id,
                )
                .filter(
                    RechnungsOPStorno.mandant_id == company.id,
                    RechnungsOPStorno.partner_id == str(partner_id),
                    Eingangsrechnung.mandant_id == company.id,
                    Eingangsrechnung.partner_id == str(partner_id),
                    RechnungsOPStorno.credit_booking_id.is_not(None),
                ).all()
            ]
        cancellation_items = (
            self._session.query(GuthabenOP.open_item_id)
            .filter(GuthabenOP.invoice_cancellation_id.in_(cancellation_ids))
            .all()
        )
        open_items = credit_note_items + cancellation_items
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
        self.reserve_credit_mutation()
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
        booking = self._session.query(Buchung).filter_by(
            booking_id=str(offset.booking_id)
        ).one_or_none()
        if booking is None:
            raise ValueError("Die Hauptbuchbuchung der Verrechnung fehlt.")
        self.ensure_credit_booking_date(
            credit=credit,
            booking_date=booking.booking_date,
        )
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
