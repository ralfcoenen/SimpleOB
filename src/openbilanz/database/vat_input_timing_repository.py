"""Repository für die zeitliche Zuordnung des Vorsteuerabzugs."""

from datetime import date
from uuid import UUID

from sqlalchemy import case
from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Buchung,
    Mandant,
    UmsatzsteuerEingangsrechnung,
    Wirtschaftsjahr,
)
from openbilanz.domain.vat_input_timing import VatInputTiming


class VatInputTimingRepository:
    """Persistiert Leistungs- und Rechnungseingangsdatum von Eingangsrechnungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        timing: VatInputTiming,
        *,
        commit: bool = True,
    ) -> None:
        """Speichert die zeitliche Zuordnung einer Eingangsrechnung."""

        if not isinstance(timing, VatInputTiming):
            raise TypeError(
                "timing must be a VatInputTiming"
            )

        booking = self._find_booking(
            timing.booking_id
        )

        if booking is None:
            raise ValueError(
                "Die zugehörige Buchung ist nicht vorhanden."
            )

        existing = (
            self._session.query(
                UmsatzsteuerEingangsrechnung
            )
            .filter(
                UmsatzsteuerEingangsrechnung.buchung_id
                == booking.id
            )
            .one_or_none()
        )

        if existing is not None:
            raise ValueError(
                "Für die Buchung ist bereits eine "
                "Vorsteuer-Zeitzuordnung vorhanden."
            )

        self._session.add(
            UmsatzsteuerEingangsrechnung(
                timing_id=str(timing.timing_id),
                buchung_id=booking.id,
                service_date=timing.service_date,
                invoice_received_date=(
                    timing.invoice_received_date
                ),
            )
        )

        if commit:
            self._session.commit()

    def get_for_booking(
        self,
        booking_id: UUID,
    ) -> VatInputTiming | None:
        """Lädt die Vorsteuer-Zeitzuordnung einer Buchung."""

        if not isinstance(booking_id, UUID):
            raise TypeError(
                "booking_id must be a UUID"
            )

        model = (
            self._session.query(
                UmsatzsteuerEingangsrechnung
            )
            .join(
                Buchung,
                UmsatzsteuerEingangsrechnung.buchung_id
                == Buchung.id,
            )
            .filter(
                Buchung.booking_id
                == str(booking_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_timing(model)

    def list_for_company_in_date_range(
        self,
        *,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[VatInputTiming, ...]:
        """Lädt Vorsteuer-Zeitzuordnungen nach maßgeblichem Abzugsdatum."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(start_date, date):
            raise TypeError(
                "start_date must be a date"
            )

        if not isinstance(end_date, date):
            raise TypeError(
                "end_date must be a date"
            )

        if end_date < start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        deductible_date = case(
            (
                UmsatzsteuerEingangsrechnung.service_date
                >= UmsatzsteuerEingangsrechnung.invoice_received_date,
                UmsatzsteuerEingangsrechnung.service_date,
            ),
            else_=(
                UmsatzsteuerEingangsrechnung.invoice_received_date
            ),
        )

        models = (
            self._session.query(
                UmsatzsteuerEingangsrechnung
            )
            .join(
                Buchung,
                UmsatzsteuerEingangsrechnung.buchung_id
                == Buchung.id,
            )
            .join(
                Wirtschaftsjahr,
                Buchung.wirtschaftsjahr_id
                == Wirtschaftsjahr.id,
            )
            .join(
                Mandant,
                Wirtschaftsjahr.mandant_id
                == Mandant.id,
            )
            .filter(
                Mandant.company_id
                == str(company_id),
                deductible_date >= start_date,
                deductible_date <= end_date,
            )
            .order_by(
                deductible_date,
                UmsatzsteuerEingangsrechnung.id,
            )
            .all()
        )

        return tuple(
            self._to_timing(model)
            for model in models
        )

    def _find_booking(
        self,
        booking_id: UUID,
    ) -> Buchung | None:
        return (
            self._session.query(Buchung)
            .filter(
                Buchung.booking_id
                == str(booking_id)
            )
            .one_or_none()
        )

    @staticmethod
    def _to_timing(
        model: UmsatzsteuerEingangsrechnung,
    ) -> VatInputTiming:
        return VatInputTiming(
            booking_id=UUID(
                model.buchung.booking_id
            ),
            service_date=model.service_date,
            invoice_received_date=(
                model.invoice_received_date
            ),
            timing_id=UUID(
                model.timing_id
            ),
        )
