"""Persistenz der Kennzeichnung von Buchungszeilen als BVV-Einlagen."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import (
    Buchung,
    Buchungszeile,
    Eigenkapitaleinlage,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.domain.equity_contribution_reference import (
    EquityContributionReference,
)
from simpleob.domain.fiscal_year import FiscalYear


class EquityContributionRepository:
    """Speichert und lädt als BVV-Einlagen gekennzeichnete Buchungszeilen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        company_id: UUID,
        reference: EquityContributionReference,
        commit: bool = True,
    ) -> None:
        """Kennzeichnet eine vorhandene Buchungszeile als BVV-Einlage."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(
            reference,
            EquityContributionReference,
        ):
            raise TypeError(
                "reference must be an EquityContributionReference"
            )

        booking_model = (
            self._session.query(Buchung)
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
                Buchung.booking_id
                == str(reference.booking_id),
                Mandant.company_id
                == str(company_id),
            )
            .one_or_none()
        )

        if booking_model is None:
            raise ValueError(
                "Die Buchung ist nicht vorhanden."
            )

        booking_line_model = (
            self._session.query(Buchungszeile)
            .filter(
                Buchungszeile.buchung_id
                == booking_model.id,
                Buchungszeile.position
                == reference.booking_line_position,
            )
            .one_or_none()
        )

        if booking_line_model is None:
            raise ValueError(
                "Die Buchungszeile ist nicht vorhanden."
            )

        existing = (
            self._session.query(Eigenkapitaleinlage)
            .filter(
                Eigenkapitaleinlage.buchungszeile_id
                == booking_line_model.id
            )
            .one_or_none()
        )

        if existing is not None:
            raise ValueError(
                "Die Buchungszeile ist bereits als "
                "BVV-Einlage gekennzeichnet."
            )

        model = Eigenkapitaleinlage(
            buchungszeile_id=booking_line_model.id,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def list_for_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> tuple[EquityContributionReference, ...]:
        """Lädt die Einlagenreferenzen eines Geschäftsjahres."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(fiscal_year, FiscalYear):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        models = (
            self._session.query(Eigenkapitaleinlage)
            .join(
                Buchungszeile,
                Eigenkapitaleinlage.buchungszeile_id
                == Buchungszeile.id,
            )
            .join(
                Buchung,
                Buchungszeile.buchung_id
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
                Wirtschaftsjahr.start_date
                == fiscal_year.start_date,
                Wirtschaftsjahr.end_date
                == fiscal_year.end_date,
            )
            .order_by(
                Buchung.booking_date,
                Buchung.id,
                Buchungszeile.position,
            )
            .all()
        )

        return tuple(
            EquityContributionReference(
                booking_id=UUID(
                    model.buchungszeile.buchung.booking_id
                ),
                booking_line_position=(
                    model.buchungszeile.position
                ),
            )
            for model in models
        )
