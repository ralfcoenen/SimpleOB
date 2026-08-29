"""Repository für umsatzsteuerliche Buchungsdetails."""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Buchung,
    Mandant,
    UmsatzsteuerBuchungsdetail,
    Wirtschaftsjahr,
)
from openbilanz.domain.vat_booking_detail import (
    VatBookingDetail,
)
from openbilanz.domain.vat_booking_direction import (
    VatBookingDirection,
)


class VatBookingDetailRepository:
    """Persistiert USt-relevante Details von Buchungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add_details(
        self,
        details: tuple[VatBookingDetail, ...],
        *,
        commit: bool = True,
    ) -> None:
        """Speichert die USt-Details einer Buchung."""

        if not details:
            return

        booking_ids = {
            detail.booking_id
            for detail in details
        }

        if len(booking_ids) != 1:
            raise ValueError(
                "Die USt-Details müssen zu derselben "
                "Buchung gehören."
            )

        booking_id = next(iter(booking_ids))

        booking = self._find_booking(
            booking_id
        )

        if booking is None:
            raise ValueError(
                "Die zugehörige Buchung ist nicht vorhanden."
            )

        existing = (
            self._session.query(
                UmsatzsteuerBuchungsdetail
            )
            .filter(
                UmsatzsteuerBuchungsdetail.buchung_id
                == booking.id
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "Für die Buchung sind bereits "
                "USt-Details vorhanden."
            )

        for detail in details:
            if not isinstance(
                detail,
                VatBookingDetail,
            ):
                raise TypeError(
                    "details must contain "
                    "VatBookingDetail instances"
                )

            self._session.add(
                UmsatzsteuerBuchungsdetail(
                    buchung_id=booking.id,
                    account_number=(
                        detail.account_number
                    ),
                    net_amount=detail.net_amount,
                    tax_amount=detail.tax_amount,
                    tax_rate=detail.tax_rate,
                    direction=detail.direction.value,
                )
            )

        if commit:
            self._session.commit()

    def list_for_booking(
        self,
        booking_id: UUID,
    ) -> tuple[VatBookingDetail, ...]:
        """Lädt die USt-Details einer Buchung."""

        booking = self._find_booking(
            booking_id
        )

        if booking is None:
            return ()

        models = (
            self._session.query(
                UmsatzsteuerBuchungsdetail
            )
            .filter(
                UmsatzsteuerBuchungsdetail.buchung_id
                == booking.id
            )
            .order_by(
                UmsatzsteuerBuchungsdetail.id
            )
            .all()
        )

        return tuple(
            VatBookingDetail(
                booking_id=booking_id,
                account_number=model.account_number,
                net_amount=model.net_amount,
                tax_amount=model.tax_amount,
                tax_rate=model.tax_rate,
                direction=VatBookingDirection(
                    model.direction
                ),
            )
            for model in models
        )

    def list_for_company_in_date_range(
        self,
        *,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[VatBookingDetail, ...]:
        """Lädt USt-Details eines Mandanten im Datumsbereich."""

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

        rows = (
            self._session.query(
                UmsatzsteuerBuchungsdetail,
                Buchung.booking_id,
            )
            .join(
                Buchung,
                UmsatzsteuerBuchungsdetail.buchung_id
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
                Buchung.booking_date
                >= start_date,
                Buchung.booking_date
                <= end_date,
            )
            .order_by(
                Buchung.booking_date,
                UmsatzsteuerBuchungsdetail.id,
            )
            .all()
        )

        return tuple(
            VatBookingDetail(
                booking_id=UUID(booking_id),
                account_number=model.account_number,
                net_amount=model.net_amount,
                tax_amount=model.tax_amount,
                tax_rate=model.tax_rate,
                direction=VatBookingDirection(
                    model.direction
                ),
            )
            for model, booking_id in rows
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
