"""Repository für Buchungen."""

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import (
    Buchung,
    Buchungszeile,
    Konto,
    Mandant,
    PersonenkontoZuordnung,
    Wirtschaftsjahr,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus


class BookingRepository:
    """Speichert und lädt Buchungen eines Geschäftsjahres."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        booking: Booking,
        commit: bool = True,
    ) -> None:
        """Speichert eine Buchung."""

        fiscal_year_model = self._find_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
            for_update=True,
        )

        if fiscal_year_model is None:
            raise ValueError(
                "Das Geschäftsjahr ist nicht vorhanden."
            )

        if (
            fiscal_year_model.status
            == FiscalYearStatus.CLOSED.value
        ):
            raise ValueError(
                "Das Geschäftsjahr ist abgeschlossen."
            )

        if not fiscal_year.contains(
            booking.booking_date
        ):
            raise ValueError(
                "Das Buchungsdatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        if booking.booking_type is BookingType.REGULAR:
            self._ensure_active_person_accounts(
                mandant_id=fiscal_year_model.mandant_id,
                booking=booking,
            )

        existing_booking = (
            self._session.query(Buchung)
            .filter(
                Buchung.booking_id
                == str(booking.booking_id)
            )
            .one_or_none()
        )

        if existing_booking is not None:
            raise ValueError(
                "Die Buchung ist bereits vorhanden."
            )

        if booking.booking_type is BookingType.REVERSAL:
            original_booking = (
                self._session.query(Buchung)
                .filter(
                    Buchung.booking_id
                    == str(
                        booking.reversal_of_booking_id
                    ),
                    Buchung.wirtschaftsjahr_id
                    == fiscal_year_model.id,
                )
                .one_or_none()
            )

            if original_booking is None:
                raise ValueError(
                    "Die ursprüngliche Buchung "
                    "ist nicht vorhanden."
                )

            if (
                original_booking.booking_type
                != BookingType.REGULAR.value
            ):
                raise ValueError(
                    "Nur reguläre Buchungen können "
                    "storniert werden."
                )

            existing_reversal = (
                self._session.query(Buchung)
                .filter(
                    Buchung.reversal_of_booking_id
                    == str(
                        booking.reversal_of_booking_id
                    )
                )
                .one_or_none()
            )

            if existing_reversal is not None:
                raise ValueError(
                    "Die ursprüngliche Buchung wurde "
                    "bereits storniert."
                )

        model = Buchung(
            booking_id=str(booking.booking_id),
            wirtschaftsjahr_id=fiscal_year_model.id,
            booking_date=booking.booking_date,
            voucher_no=booking.voucher_no,
            description=booking.description,
            booking_type=booking.booking_type.value,
            reversal_of_booking_id=(
                str(booking.reversal_of_booking_id)
                if booking.reversal_of_booking_id is not None
                else None
            ),
        )

        model.zeilen = [
            Buchungszeile(
                position=position,
                account_number=line.account_number,
                side=line.side.value,
                amount=line.amount,
            )
            for position, line in enumerate(
                booking.lines
            )
        ]

        self._session.add(model)

        if commit:
            self._session.commit()

    def _ensure_active_person_accounts(
        self,
        *,
        mandant_id: int,
        booking: Booking,
    ) -> None:
        """Sperrt neue reguläre Buchungen auf inaktive Personenkonten.

        Eröffnungsbuchungen und Stornierungen verwenden einen eigenen
        Buchungstyp und bleiben absichtlich von dieser Prüfung ausgenommen.
        """

        account_numbers = {
            line.account_number for line in booking.lines
        }
        inactive = (
            self._session.query(Konto.account_number)
            .join(
                PersonenkontoZuordnung,
                (PersonenkontoZuordnung.mandant_id == Konto.mandant_id)
                & (PersonenkontoZuordnung.account_number == Konto.account_number),
            )
            .filter(
                Konto.mandant_id == mandant_id,
                Konto.account_number.in_(account_numbers),
                Konto.is_active.is_(False),
            )
            .order_by(Konto.account_number)
            .all()
        )
        if inactive:
            numbers = ", ".join(row[0] for row in inactive)
            raise ValueError(
                "Neue reguläre Buchungen auf inaktive Personenkonten sind "
                f"nicht zulässig: {numbers}."
            )

    def commit(self) -> None:
        """Bestätigt die aktuelle Datenbanktransaktion."""

        self._session.commit()

    def rollback(self) -> None:
        """Verwirft die aktuelle Datenbanktransaktion."""

        self._session.rollback()

    def require_open_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        booking_date: date,
        for_update: bool = False,
    ) -> Wirtschaftsjahr:
        """Lädt ein offenes Zieljahr und prüft dessen Buchungsdatum."""

        fiscal_year_model = self._find_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
            for_update=for_update,
        )
        if fiscal_year_model is None:
            raise ValueError("Das Geschäftsjahr gehört nicht zum geöffneten Mandanten.")
        if fiscal_year_model.status != FiscalYearStatus.OPEN.value:
            raise ValueError("Das Geschäftsjahr ist nicht offen.")
        if not fiscal_year.contains(booking_date):
            raise ValueError("Das Stornobuchungsdatum liegt außerhalb des Geschäftsjahrs.")
        return fiscal_year_model

    def get(
        self,
        booking_id: UUID,
    ) -> Booking | None:
        """Lädt eine Buchung über ihre fachliche ID."""

        if not isinstance(
            booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        model = (
            self._session.query(Buchung)
            .filter(
                Buchung.booking_id
                == str(booking_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return Booking(
            booking_id=UUID(model.booking_id),
            booking_date=model.booking_date,
            voucher_no=model.voucher_no,
            description=model.description,
            booking_type=BookingType(
                model.booking_type
            ),
            lines=tuple(
                BookingLine(
                    account_number=line.account_number,
                    side=EntrySide.from_value(
                        line.side
                    ),
                    amount=line.amount,
                )
                for line in model.zeilen
            ),
            reversal_of_booking_id=(
                UUID(model.reversal_of_booking_id)
                if model.reversal_of_booking_id is not None
                else None
            ),
        )

    def is_reversed(
        self,
        booking_id: UUID,
    ) -> bool:
        """Prüft, ob eine Buchung storniert wurde."""

        if not isinstance(
            booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        reversal = (
            self._session.query(Buchung)
            .filter(
                Buchung.reversal_of_booking_id
                == str(booking_id)
            )
            .one_or_none()
        )

        return reversal is not None

    def list_for_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> tuple[Booking, ...]:
        """Lädt alle Buchungen eines Geschäftsjahres."""

        fiscal_year_model = self._find_fiscal_year(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

        if fiscal_year_model is None:
            return ()

        models = (
            self._session.query(Buchung)
            .filter(
                Buchung.wirtschaftsjahr_id
                == fiscal_year_model.id
            )
            .order_by(
                Buchung.booking_date,
                Buchung.id,
            )
            .all()
        )

        return tuple(
            Booking(
                booking_id=UUID(model.booking_id),
                booking_date=model.booking_date,
                voucher_no=model.voucher_no,
                description=model.description,
                booking_type=BookingType(
                    model.booking_type
                ),
                lines=tuple(
                    BookingLine(
                        account_number=line.account_number,
                        side=EntrySide.from_value(
                            line.side
                        ),
                        amount=line.amount,
                    )
                    for line in model.zeilen
                ),
                reversal_of_booking_id=(
                    UUID(model.reversal_of_booking_id)
                    if model.reversal_of_booking_id is not None
                    else None
                ),
            )
            for model in models
        )

    def _find_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        for_update: bool = False,
    ) -> Wirtschaftsjahr | None:
        """Findet das persistierte Geschäftsjahr und sperrt es optional."""

        query = (
            self._session.query(Wirtschaftsjahr)
            .join(Mandant)
            .filter(
                Mandant.company_id == str(company_id),
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
        )

        use_postgresql_lock = (
            for_update
            and self._session.get_bind().dialect.name == "postgresql"
        )

        if use_postgresql_lock:
            try:
                self._session.execute(
                    text("SET LOCAL lock_timeout = '3000ms'")
                )

                return (
                    query.with_for_update(of=Wirtschaftsjahr)
                    .populate_existing()
                    .one_or_none()
                )

            except OperationalError as exc:
                sqlstate = getattr(exc.orig, "sqlstate", None)

                if sqlstate != "55P03":
                    raise

                self._session.rollback()

                raise DatabaseLockError(
                    "Das Geschäftsjahr ist momentan durch einen "
                    "anderen Vorgang gesperrt. "
                    "Es wurden keine Änderungen gespeichert. "
                    "Bitte versuchen Sie es erneut."
                ) from exc

        return query.one_or_none()
