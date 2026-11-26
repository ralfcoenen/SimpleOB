"""Persistiert die eindeutige Verbindung externer Bankumsätze zu Buchungen."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import (
    BankTransactionBooking,
    Buchung,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.domain.bank_transaction import BankImportSource


class BankTransactionBookingRepository:
    """Mandantenbezogene Duplikatprüfung und Zuordnung zu Buchungen."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_company(self, company_id: UUID) -> tuple[tuple[str, str, UUID], ...]:
        """Liefert externe Kennungen und Buchungs-UUIDs eines Mandanten."""
        company = self._company(company_id)
        rows = (
            self._session.query(BankTransactionBooking)
            .filter(BankTransactionBooking.mandant_id == company.id)
            .order_by(BankTransactionBooking.import_source, BankTransactionBooking.external_transaction_id)
            .all()
        )
        return tuple((row.import_source, row.external_transaction_id, UUID(row.booking_id)) for row in rows)

    def booking_id_for(
        self,
        *,
        company_id: UUID,
        import_source: BankImportSource,
        external_transaction_id: str,
    ) -> UUID | None:
        """Liefert die Buchungs-ID, wenn der Umsatz bereits übernommen wurde."""
        if not isinstance(import_source, BankImportSource):
            raise TypeError("import_source muss eine BankImportSource sein.")
        company = self._company(company_id)
        model = (
            self._session.query(BankTransactionBooking)
            .filter(
                BankTransactionBooking.mandant_id == company.id,
                BankTransactionBooking.import_source == import_source.value,
                BankTransactionBooking.external_transaction_id
                == _validate_external_id(external_transaction_id),
            )
            .one_or_none()
        )
        return UUID(model.booking_id) if model is not None else None

    def add(
        self,
        *,
        company_id: UUID,
        import_source: BankImportSource,
        external_transaction_id: str,
        booking_id: UUID,
        commit: bool = True,
    ) -> None:
        """Speichert eine Importzuordnung, optional innerhalb einer Sammeltransaktion."""
        if not isinstance(import_source, BankImportSource):
            raise TypeError("import_source muss eine BankImportSource sein.")
        if not isinstance(booking_id, UUID):
            raise TypeError("booking_id muss eine UUID sein.")
        company = self._company(company_id)
        external_id = _validate_external_id(external_transaction_id)

        # Das Query löst ein mögliches Autoflush der zuvor angefügten Buchung aus.
        linked_booking_exists = (
            self._session.query(Buchung.booking_id)
            .join(Wirtschaftsjahr, Buchung.wirtschaftsjahr_id == Wirtschaftsjahr.id)
            .filter(
                Buchung.booking_id == str(booking_id),
                Wirtschaftsjahr.mandant_id == company.id,
            )
            .one_or_none()
        )
        if linked_booking_exists is None:
            raise ValueError("Die Buchung gehört nicht zum angegebenen Mandanten.")

        self._session.add(
            BankTransactionBooking(
                mandant_id=company.id,
                import_source=import_source.value,
                external_transaction_id=external_id,
                booking_id=str(booking_id),
            )
        )
        if commit:
            self._session.commit()

    def _company(self, company_id: UUID) -> Mandant:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id muss eine UUID sein.")
        company = (
            self._session.query(Mandant)
            .filter(Mandant.company_id == str(company_id))
            .one_or_none()
        )
        if company is None:
            raise ValueError("Das Unternehmen ist nicht vorhanden.")
        return company


def _validate_external_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("external_transaction_id muss eine Zeichenkette sein.")
    normalized = value.strip()
    if not normalized:
        raise ValueError("external_transaction_id darf nicht leer sein.")
    return normalized
