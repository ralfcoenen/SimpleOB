"""Persistenz für gebuchte Ausgangsrechnungen und Forderungs-OPs."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    ForderungsOP,
    Geschaeftspartner,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.receivable_invoice import (
    ReceivableInvoice,
    ReceivableOpenItem,
)


class ReceivableInvoiceRepository:
    """Speichert Rechnung und genau einen Forderungs-OP in der Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        invoice: ReceivableInvoice,
        open_item: ReceivableOpenItem,
        fiscal_year: FiscalYear,
        commit: bool = True,
    ) -> None:
        if not isinstance(invoice, ReceivableInvoice):
            raise TypeError("invoice must be a ReceivableInvoice")
        if not isinstance(open_item, ReceivableOpenItem):
            raise TypeError("open_item must be a ReceivableOpenItem")
        if open_item.invoice_id != invoice.invoice_id:
            raise ValueError("Der OP verweist auf eine andere Rechnung.")
        if open_item.amount != invoice.gross_amount:
            raise ValueError("Rechnungsbetrag und OP-Betrag stimmen nicht überein.")

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
                Geschaeftspartner.is_customer.is_(True),
                Geschaeftspartner.is_active.is_(True),
            )
            .one_or_none()
        )
        if partner is None:
            raise ValueError(
                "Der aktive Kunde gehört nicht zum geöffneten Mandanten."
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
                "Die Hauptbuchbuchung fehlt oder gehört zu einem anderen Geschäftsjahr."
            )

        if self._session.query(Ausgangsrechnung.id).filter(
            Ausgangsrechnung.invoice_id == str(invoice.invoice_id)
        ).one_or_none():
            raise ValueError("Die Rechnungs-ID ist bereits vorhanden.")
        if self._session.query(ForderungsOP.id).filter(
            ForderungsOP.open_item_id == str(open_item.open_item_id)
        ).one_or_none():
            raise ValueError("Die OP-ID ist bereits vorhanden.")
        if self._session.query(Ausgangsrechnung.id).filter(
            Ausgangsrechnung.booking_id == str(invoice.booking_id)
        ).one_or_none():
            raise ValueError(
                "Für diese Hauptbuchbuchung existiert bereits eine Rechnung."
            )
        if self._session.query(Ausgangsrechnung.id).filter(
            Ausgangsrechnung.mandant_id == company.id,
            Ausgangsrechnung.invoice_number == invoice.invoice_number,
        ).one_or_none():
            raise ValueError(
                "Diese Rechnungsnummer ist im Mandanten bereits vergeben."
            )

        self._session.add(
            Ausgangsrechnung(
                invoice_id=str(invoice.invoice_id),
                mandant_id=company.id,
                partner_id=str(invoice.partner_id),
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                gross_amount=invoice.gross_amount,
                booking_id=str(invoice.booking_id),
            )
        )
        self._session.add(
            ForderungsOP(
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
    ) -> ReceivableOpenItem | None:
        model = (
            self._session.query(ForderungsOP)
            .filter(ForderungsOP.invoice_id == str(invoice_id))
            .one_or_none()
        )
        if model is None:
            return None
        return ReceivableOpenItem(
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
            self._session.query(ForderungsOP)
            .join(Ausgangsrechnung)
            .filter(Ausgangsrechnung.mandant_id == company.id)
            .count()
        )
