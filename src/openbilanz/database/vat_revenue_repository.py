"""Repository für umsatzsteuerliche Ausgangsumsätze."""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Buchung,
    Mandant,
    UmsatzsteuerAusgangsumsatz,
    UmsatzsteuerZahlungszuordnung,
    Wirtschaftsjahr,
)
from openbilanz.domain.vat_payment_allocation import (
    VatPaymentAllocation,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


class VatRevenueRepository:
    """Persistiert Ausgangsumsätze und Zahlungszuordnungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add_revenue(
        self,
        revenue: VatRevenue,
        *,
        commit: bool = True,
    ) -> None:
        """Speichert einen Ausgangsumsatz."""

        if not isinstance(revenue, VatRevenue):
            raise TypeError(
                "revenue must be a VatRevenue"
            )

        booking = self._find_booking(
            revenue.booking_id
        )

        if booking is None:
            raise ValueError(
                "Die zugehörige Buchung ist nicht vorhanden."
            )

        existing = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .filter(
                UmsatzsteuerAusgangsumsatz.buchung_id
                == booking.id
            )
            .one_or_none()
        )

        if existing is not None:
            raise ValueError(
                "Für die Buchung ist bereits ein "
                "Ausgangsumsatz vorhanden."
            )

        model = UmsatzsteuerAusgangsumsatz(
            revenue_id=str(revenue.revenue_id),
            buchung_id=booking.id,
            gross_amount=revenue.gross_amount,
            revenue_kind=revenue.revenue_kind.value,
            payment_kind=revenue.payment_kind.value,
            service_date=revenue.service_date,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def add_payment_allocation(
        self,
        allocation: VatPaymentAllocation,
        *,
        commit: bool = True,
    ) -> None:
        """Ordnet eine Zahlung einem Ausgangsumsatz zu."""

        if not isinstance(
            allocation,
            VatPaymentAllocation,
        ):
            raise TypeError(
                "allocation must be a VatPaymentAllocation"
            )

        revenue_model = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .filter(
                UmsatzsteuerAusgangsumsatz.revenue_id
                == str(allocation.revenue_id)
            )
            .one_or_none()
        )

        if revenue_model is None:
            raise ValueError(
                "Der Ausgangsumsatz ist nicht vorhanden."
            )

        if (
            revenue_model.payment_kind
            == VatPaymentKind.IMMEDIATE.value
        ):
            raise ValueError(
                "Ein sofort vereinnahmter Ausgangsumsatz "
                "benötigt keine Zahlungszuordnung."
            )

        payment_booking = self._find_booking(
            allocation.payment_booking_id
        )

        if payment_booking is None:
            raise ValueError(
                "Die Zahlungsbuchung ist nicht vorhanden."
            )

        allocated_amount = sum(
            (
                item.amount
                for item in revenue_model.zahlungszuordnungen
            ),
            start=0,
        )

        if (
            allocated_amount + allocation.amount
            > revenue_model.gross_amount
        ):
            raise ValueError(
                "Die Zahlungszuordnungen überschreiten "
                "den Ausgangsumsatz."
            )

        model = UmsatzsteuerZahlungszuordnung(
            allocation_id=str(
                allocation.allocation_id
            ),
            ausgangsumsatz_id=revenue_model.id,
            zahlungsbuchung_id=payment_booking.id,
            amount=allocation.amount,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def get_revenue(
        self,
        revenue_id: UUID,
    ) -> VatRevenue | None:
        """Lädt einen Ausgangsumsatz."""

        if not isinstance(revenue_id, UUID):
            raise TypeError(
                "revenue_id must be a UUID"
            )

        model = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .filter(
                UmsatzsteuerAusgangsumsatz.revenue_id
                == str(revenue_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_revenue(model)

    def list_allocations_for_revenue(
        self,
        revenue_id: UUID,
    ) -> tuple[VatPaymentAllocation, ...]:
        """Lädt die Zahlungszuordnungen eines Ausgangsumsatzes."""

        if not isinstance(revenue_id, UUID):
            raise TypeError(
                "revenue_id must be a UUID"
            )

        revenue_model = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .filter(
                UmsatzsteuerAusgangsumsatz.revenue_id
                == str(revenue_id)
            )
            .one_or_none()
        )

        if revenue_model is None:
            return ()

        return tuple(
            VatPaymentAllocation(
                revenue_id=revenue_id,
                payment_booking_id=UUID(
                    model.zahlungsbuchung.booking_id
                ),
                amount=model.amount,
                allocation_id=UUID(
                    model.allocation_id
                ),
            )
            for model in revenue_model.zahlungszuordnungen
        )

    def list_revenues_for_company(
        self,
        *,
        company_id: UUID,
    ) -> tuple[VatRevenue, ...]:
        """Lädt alle Ausgangsumsätze eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        models = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .join(
                Buchung,
                UmsatzsteuerAusgangsumsatz.buchung_id
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
                == str(company_id)
            )
            .order_by(
                Buchung.booking_date,
                UmsatzsteuerAusgangsumsatz.id,
            )
            .all()
        )

        return tuple(
            self._to_revenue(model)
            for model in models
        )

    def list_revenues_for_company_in_date_range(
        self,
        *,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[VatRevenue, ...]:
        """Lädt Ausgangsumsätze eines Mandanten im Datumsbereich."""

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

        models = (
            self._session.query(
                UmsatzsteuerAusgangsumsatz
            )
            .join(
                Buchung,
                UmsatzsteuerAusgangsumsatz.buchung_id
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
                UmsatzsteuerAusgangsumsatz.service_date
                >= start_date,
                UmsatzsteuerAusgangsumsatz.service_date
                <= end_date,
            )
            .order_by(
                UmsatzsteuerAusgangsumsatz.service_date,
                UmsatzsteuerAusgangsumsatz.id,
            )
            .all()
        )

        return tuple(
            self._to_revenue(model)
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
    def _to_revenue(
        model: UmsatzsteuerAusgangsumsatz,
    ) -> VatRevenue:
        return VatRevenue(
            booking_id=UUID(
                model.buchung.booking_id
            ),
            gross_amount=model.gross_amount,
            revenue_kind=VatRevenueKind(
                model.revenue_kind
            ),
            payment_kind=VatPaymentKind(
                model.payment_kind
            ),
            service_date=model.service_date,
            revenue_id=UUID(
                model.revenue_id
            ),
        )
