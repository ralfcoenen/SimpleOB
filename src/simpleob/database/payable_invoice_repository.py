"""Persistenz für Eingangsrechnungen und Verbindlichkeits-OPs."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import (
    Buchung,
    Eingangsrechnung,
    Geschaeftspartner,
    Mandant,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.payable_invoice import (
    DuplicateSupplierInvoiceError,
    PayableInvoice,
    PayableOpenItem,
)


class PayableInvoiceRepository:
    """Speichert Rechnung und Verbindlichkeits-OP in derselben Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        invoice: PayableInvoice,
        open_item: PayableOpenItem,
        fiscal_year: FiscalYear,
        commit: bool = True,
    ) -> None:
        if not isinstance(invoice, PayableInvoice):
            raise TypeError("invoice must be a PayableInvoice")
        if not isinstance(open_item, PayableOpenItem):
            raise TypeError("open_item must be a PayableOpenItem")
        if open_item.invoice_id != invoice.invoice_id:
            raise ValueError("Der OP verweist auf eine andere Rechnung.")
        if open_item.amount != invoice.gross_amount:
            raise ValueError(
                "Rechnungsbetrag und OP-Betrag stimmen nicht überein."
            )

        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(invoice.company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")

        partner = (
            self._session.query(Geschaeftspartner)
            .filter(
                Geschaeftspartner.mandant_id == company.id,
                Geschaeftspartner.partner_id == str(invoice.partner_id),
                Geschaeftspartner.is_supplier.is_(True),
                Geschaeftspartner.is_active.is_(True),
            )
            .one_or_none()
        )
        if partner is None:
            raise ValueError(
                "Der aktive Lieferant gehört nicht zum geöffneten Mandanten."
            )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .join(Mandant)
            .filter(
                Mandant.company_id == str(invoice.company_id),
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
                Buchung.booking_id == str(invoice.booking_id),
                Buchung.wirtschaftsjahr_id == fiscal_year_model.id,
            )
            .one_or_none()
        )
        if booking_exists is None:
            raise ValueError(
                "Die Hauptbuchbuchung fehlt oder gehört zu einem anderen "
                "Geschäftsjahr."
            )

        if self._session.query(Eingangsrechnung.id).filter(
            Eingangsrechnung.invoice_id == str(invoice.invoice_id)
        ).one_or_none():
            raise ValueError("Die Rechnungs-ID ist bereits vorhanden.")
        if self._session.query(VerbindlichkeitsOP.id).filter(
            VerbindlichkeitsOP.open_item_id == str(open_item.open_item_id)
        ).one_or_none():
            raise ValueError("Die OP-ID ist bereits vorhanden.")
        if self._session.query(Eingangsrechnung.id).filter(
            Eingangsrechnung.booking_id == str(invoice.booking_id)
        ).one_or_none():
            raise ValueError(
                "Für diese Hauptbuchbuchung existiert bereits eine "
                "Eingangsrechnung."
            )

        duplicate_query = self._session.query(Eingangsrechnung.id).filter(
            Eingangsrechnung.mandant_id == company.id,
            Eingangsrechnung.partner_id == str(invoice.partner_id),
            Eingangsrechnung.invoice_number == invoice.invoice_number,
        )
        duplicate_exists = duplicate_query.one_or_none() is not None
        duplicate_reason = invoice.duplicate_reason
        if duplicate_exists and duplicate_reason is None:
            raise DuplicateSupplierInvoiceError(invoice.invoice_number)
        if not duplicate_exists and duplicate_reason is not None:
            raise ValueError(
                "Eine Duplikatbegründung ist nur bei einer bereits "
                "vorhandenen Rechnungsnummer zulässig."
            )

        self._session.add(
            Eingangsrechnung(
                invoice_id=str(invoice.invoice_id),
                mandant_id=company.id,
                partner_id=str(invoice.partner_id),
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                gross_amount=invoice.gross_amount,
                booking_id=str(invoice.booking_id),
                duplicate_reason=duplicate_reason,
            )
        )
        self._session.add(
            VerbindlichkeitsOP(
                open_item_id=str(open_item.open_item_id),
                invoice_id=str(open_item.invoice_id),
                amount=open_item.amount,
            )
        )
        if commit:
            self._session.commit()

    def get_open_item(
        self,
        invoice_id: UUID,
    ) -> PayableOpenItem | None:
        model = (
            self._session.query(VerbindlichkeitsOP)
            .filter(VerbindlichkeitsOP.invoice_id == str(invoice_id))
            .one_or_none()
        )
        if model is None:
            return None
        return PayableOpenItem(
            invoice_id=UUID(model.invoice_id),
            open_item_id=UUID(model.open_item_id),
            amount=model.amount,
        )

    def count_for_company(self, company_id: UUID) -> int:
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            return 0
        return (
            self._session.query(VerbindlichkeitsOP)
            .join(Eingangsrechnung)
            .filter(Eingangsrechnung.mandant_id == company.id)
            .count()
        )
