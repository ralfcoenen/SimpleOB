"""Persistenz für Gutschriften, Guthaben-OPs und deren Ereignisse."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Eingangsrechnung,
    Geschaeftspartner,
    GuthabenOP,
    GuthabenOPEreignis,
    Gutschrift,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.domain.credit_note import (
    CreditBalanceOpenItem,
    CreditNote,
    CreditNoteKind,
    DuplicateSupplierCreditNoteError,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO


class CreditNoteRepository:
    """Speichert Gutschrift und Guthaben-OP in derselben SQLAlchemy-Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        credit_note: CreditNote,
        open_item: CreditBalanceOpenItem,
        fiscal_year: FiscalYear,
        commit: bool = True,
    ) -> None:
        if not isinstance(credit_note, CreditNote):
            raise TypeError("credit_note must be a CreditNote")
        if not isinstance(open_item, CreditBalanceOpenItem):
            raise TypeError("open_item must be a CreditBalanceOpenItem")
        if open_item.credit_note_id != credit_note.credit_note_id:
            raise ValueError("Der Guthaben-OP verweist auf eine andere Gutschrift.")
        if open_item.amount != credit_note.gross_amount:
            raise ValueError("Gutschriftbetrag und Guthaben-OP stimmen nicht überein.")

        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(credit_note.company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")

        customer_note = credit_note.kind is CreditNoteKind.CUSTOMER
        partner_role = (
            Geschaeftspartner.is_customer
            if customer_note
            else Geschaeftspartner.is_supplier
        )
        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(credit_note.partner_id),
                partner_role.is_(True),
                Geschaeftspartner.is_active.is_(True),
            )
            .one_or_none()
        )
        if partner is None:
            role_label = "Kunde" if customer_note else "Lieferant"
            raise ValueError(
                f"Der aktive {role_label} gehört nicht zum geöffneten Mandanten."
            )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .join(Mandant)
            .filter(
                Mandant.company_id == str(credit_note.company_id),
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
            .one_or_none()
        )
        if fiscal_year_model is None:
            raise ValueError("Das Geschäftsjahr gehört nicht zum Mandanten.")
        booking_exists = (
            self._session.query(Buchung.id)
            .filter(
                Buchung.booking_id == str(credit_note.booking_id),
                Buchung.wirtschaftsjahr_id == fiscal_year_model.id,
            )
            .one_or_none()
        )
        if booking_exists is None:
            raise ValueError(
                "Die Hauptbuchbuchung fehlt oder gehört zu einem anderen "
                "Geschäftsjahr."
            )

        if self._session.query(Gutschrift.id).filter(
            Gutschrift.credit_note_id == str(credit_note.credit_note_id)
        ).one_or_none():
            raise ValueError("Die Gutschrift-ID ist bereits vorhanden.")
        if self._session.query(GuthabenOP.id).filter(
            GuthabenOP.open_item_id == str(open_item.open_item_id)
        ).one_or_none():
            raise ValueError("Die Guthaben-OP-ID ist bereits vorhanden.")
        if self._session.query(Gutschrift.id).filter(
            Gutschrift.booking_id == str(credit_note.booking_id)
        ).one_or_none():
            raise ValueError(
                "Für diese Hauptbuchbuchung existiert bereits eine Gutschrift."
            )

        self._validate_original_invoice(
            credit_note=credit_note,
            company_id=company.id,
        )
        duplicate_exists = self._duplicate_exists(
            credit_note=credit_note,
            company_id=company.id,
        )
        if credit_note.kind is CreditNoteKind.SUPPLIER:
            if duplicate_exists and credit_note.duplicate_reason is None:
                raise DuplicateSupplierCreditNoteError(credit_note.note_number)
            if not duplicate_exists and credit_note.duplicate_reason is not None:
                raise ValueError(
                    "Eine Duplikatbegründung ist nur bei einer bereits "
                    "vorhandenen Lieferantengutschriftnummer zulässig."
                )
        elif duplicate_exists:
            raise ValueError(
                "Diese Kundengutschriftnummer ist im Mandanten bereits vergeben."
            )

        original_receivable_id = None
        original_payable_id = None
        if credit_note.original_invoice_id is not None:
            if customer_note:
                original_receivable_id = str(credit_note.original_invoice_id)
            else:
                original_payable_id = str(credit_note.original_invoice_id)

        self._session.add(
            Gutschrift(
                credit_note_id=str(credit_note.credit_note_id),
                mandant_id=company.id,
                partner_id=str(credit_note.partner_id),
                credit_note_kind=credit_note.kind.value,
                note_number=credit_note.note_number,
                note_date=credit_note.note_date,
                original_receivable_invoice_id=original_receivable_id,
                original_payable_invoice_id=original_payable_id,
                booking_id=str(credit_note.booking_id),
                duplicate_reason=credit_note.duplicate_reason,
            )
        )
        self._session.flush()
        self._session.add(
            GuthabenOP(
                open_item_id=str(open_item.open_item_id),
                credit_note_id=str(open_item.credit_note_id),
                amount=open_item.amount,
            )
        )
        if commit:
            self._session.commit()

    def resolve_original_invoice_id(
        self,
        *,
        company_id: UUID,
        partner_id: UUID,
        kind: CreditNoteKind,
        invoice_number: str,
    ) -> UUID:
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        invoice_model = (
            Ausgangsrechnung
            if kind is CreditNoteKind.CUSTOMER
            else Eingangsrechnung
        )
        matches = (
            self._session.query(invoice_model.invoice_id)
            .filter(
                invoice_model.mandant_id == company.id,
                invoice_model.partner_id == str(partner_id),
                invoice_model.invoice_number == invoice_number.strip(),
            )
            .all()
        )
        if len(matches) != 1:
            raise ValueError(
                "Die Rechnungsreferenz muss genau eine Rechnung dieses "
                "Partners im geöffneten Mandanten bezeichnen."
            )
        return UUID(matches[0][0])

    def _validate_original_invoice(
        self,
        *,
        credit_note: CreditNote,
        company_id: int,
    ) -> None:
        if credit_note.original_invoice_id is None:
            return
        invoice_model = (
            Ausgangsrechnung
            if credit_note.kind is CreditNoteKind.CUSTOMER
            else Eingangsrechnung
        )
        original = (
            self._session.query(invoice_model.id)
            .filter(
                invoice_model.mandant_id == company_id,
                invoice_model.partner_id == str(credit_note.partner_id),
                invoice_model.invoice_id == str(credit_note.original_invoice_id),
            )
            .one_or_none()
        )
        if original is None:
            raise ValueError(
                "Die referenzierte Rechnung gehört nicht zu diesem Partner "
                "und Mandanten oder existiert nicht."
            )

    def _duplicate_exists(
        self,
        *,
        credit_note: CreditNote,
        company_id: int,
    ) -> bool:
        if credit_note.kind is CreditNoteKind.CUSTOMER:
            return (
                self._session.query(Ausgangsrechnung.id)
                .filter(
                    Ausgangsrechnung.mandant_id == company_id,
                    Ausgangsrechnung.invoice_number == credit_note.note_number,
                )
                .first()
                is not None
                or self._session.query(Gutschrift.id)
                .filter(
                    Gutschrift.mandant_id == company_id,
                    Gutschrift.credit_note_kind == CreditNoteKind.CUSTOMER.value,
                    Gutschrift.note_number == credit_note.note_number,
                )
                .first()
                is not None
            )
        return (
            self._session.query(Eingangsrechnung.id)
            .filter(
                Eingangsrechnung.mandant_id == company_id,
                Eingangsrechnung.partner_id == str(credit_note.partner_id),
                Eingangsrechnung.invoice_number == credit_note.note_number,
            )
            .first()
            is not None
            or self._session.query(Gutschrift.id)
            .filter(
                Gutschrift.mandant_id == company_id,
                Gutschrift.partner_id == str(credit_note.partner_id),
                Gutschrift.credit_note_kind == CreditNoteKind.SUPPLIER.value,
                Gutschrift.note_number == credit_note.note_number,
            )
            .first()
            is not None
        )

    def get_open_item(
        self,
        credit_note_id: UUID,
    ) -> CreditBalanceOpenItem | None:
        model = (
            self._session.query(GuthabenOP)
            .filter(GuthabenOP.credit_note_id == str(credit_note_id))
            .one_or_none()
        )
        if model is None:
            return None
        return CreditBalanceOpenItem(
            credit_note_id=UUID(model.credit_note_id),
            open_item_id=UUID(model.open_item_id),
            amount=model.amount,
        )

    def get_open_amount(self, open_item_id: UUID) -> Decimal | None:
        model = (
            self._session.query(GuthabenOP)
            .filter(GuthabenOP.open_item_id == str(open_item_id))
            .one_or_none()
        )
        if model is None:
            return None
        event_total = (
            self._session.query(func.sum(GuthabenOPEreignis.amount_delta))
            .filter(GuthabenOPEreignis.open_item_id == str(open_item_id))
            .scalar()
        )
        open_amount = model.amount + (event_total or ZERO)
        if open_amount < ZERO:
            raise ValueError(
                "Die Guthaben-OP-Ereignisse reduzieren den Ursprungsbetrag "
                "unter null."
            )
        return open_amount

    def count_for_company(self, company_id: UUID) -> int:
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            return 0
        return (
            self._session.query(GuthabenOP)
            .join(Gutschrift)
            .filter(Gutschrift.mandant_id == company.id)
            .count()
        )
