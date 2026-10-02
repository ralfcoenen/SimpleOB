"""Persistenz bestätigter Buchungen zur Ergebnisverwendung."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Buchung,
    Buchungszeile,
    Gewinnverwendungsbuchung,
    Mandant,
    Wirtschaftsjahr,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.profit_appropriation_posting import (
    ProfitAppropriationPosting,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


class ProfitAppropriationPostingRepository:
    """Speichert und lädt bestätigte Ergebnisverwendungsbuchungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        company_id: UUID,
        posting: ProfitAppropriationPosting,
        booking_line_position: int,
        commit: bool = True,
    ) -> None:
        """Speichert eine bestätigte Ergebnisverwendungsbuchung."""

        if not isinstance(
            company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            posting,
            ProfitAppropriationPosting,
        ):
            raise TypeError(
                "posting must be a "
                "ProfitAppropriationPosting"
            )

        if not isinstance(
            booking_line_position,
            int,
        ):
            raise TypeError(
                "booking_line_position must be an int"
            )

        if booking_line_position < 0:
            raise ValueError(
                "booking_line_position must not be negative"
            )

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Der Mandant ist nicht vorhanden."
            )

        source_fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.end_date
                == posting.source_fiscal_year_end,
            )
            .one_or_none()
        )

        if source_fiscal_year_model is None:
            raise ValueError(
                "Das Quellgeschäftsjahr ist nicht vorhanden."
            )

        booking_model = (
            self._session.query(Buchung)
            .join(
                Wirtschaftsjahr,
                Buchung.wirtschaftsjahr_id
                == Wirtschaftsjahr.id,
            )
            .filter(
                Buchung.booking_id
                == str(posting.booking_id),
                Wirtschaftsjahr.mandant_id
                == company_model.id,
            )
            .one_or_none()
        )

        if booking_model is None:
            raise ValueError(
                "Die Ergebnisverwendungsbuchung "
                "ist nicht vorhanden."
            )

        if booking_model.booking_date != posting.posting_date:
            raise ValueError(
                "Das Buchungsdatum stimmt nicht mit "
                "der Ergebnisverwendungsbuchung überein."
            )

        booking_line_model = (
            self._session.query(Buchungszeile)
            .filter(
                Buchungszeile.buchung_id
                == booking_model.id,
                Buchungszeile.position
                == booking_line_position,
            )
            .one_or_none()
        )

        if booking_line_model is None:
            raise ValueError(
                "Die Buchungszeile ist nicht vorhanden."
            )

        if booking_line_model.amount != posting.amount:
            raise ValueError(
                "Der Betrag der Buchungszeile stimmt "
                "nicht mit der Ergebnisverwendungsbuchung "
                "überein."
            )

        existing_posting = (
            self._session.query(
                Gewinnverwendungsbuchung
            )
            .filter(
                Gewinnverwendungsbuchung.posting_id
                == str(posting.posting_id)
            )
            .one_or_none()
        )

        if existing_posting is not None:
            raise ValueError(
                "Die Ergebnisverwendungsbuchung "
                "ist bereits vorhanden."
            )

        existing_booking_line = (
            self._session.query(
                Gewinnverwendungsbuchung
            )
            .filter(
                Gewinnverwendungsbuchung.buchungszeile_id
                == booking_line_model.id
            )
            .one_or_none()
        )

        if existing_booking_line is not None:
            raise ValueError(
                "Die Buchungszeile ist bereits einer "
                "Ergebnisverwendungsbuchung zugeordnet."
            )

        model = Gewinnverwendungsbuchung(
            posting_id=str(
                posting.posting_id
            ),
            quell_wirtschaftsjahr_id=(
                source_fiscal_year_model.id
            ),
            buchungszeile_id=booking_line_model.id,
            posting_date=posting.posting_date,
            amount=posting.amount,
            posting_type=posting.posting_type.value,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def get(
        self,
        posting_id: UUID,
    ) -> ProfitAppropriationPosting | None:
        """Lädt eine Ergebnisverwendungsbuchung über ihre fachliche ID."""

        if not isinstance(
            posting_id,
            UUID,
        ):
            raise TypeError(
                "posting_id must be a UUID"
            )

        model = (
            self._session.query(
                Gewinnverwendungsbuchung
            )
            .filter(
                Gewinnverwendungsbuchung.posting_id
                == str(posting_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def list_for_source_fiscal_year(
        self,
        *,
        company_id: UUID,
        source_fiscal_year_end: date,
    ) -> tuple[ProfitAppropriationPosting, ...]:
        """Lädt alle Umsetzungsbuchungen eines Quellgeschäftsjahrs."""

        if not isinstance(
            company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            source_fiscal_year_end,
            date,
        ):
            raise TypeError(
                "source_fiscal_year_end must be a date"
            )

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            return ()

        source_fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.end_date
                == source_fiscal_year_end,
            )
            .one_or_none()
        )

        if source_fiscal_year_model is None:
            return ()

        models = (
            self._session.query(
                Gewinnverwendungsbuchung
            )
            .filter(
                Gewinnverwendungsbuchung.quell_wirtschaftsjahr_id
                == source_fiscal_year_model.id
            )
            .order_by(
                Gewinnverwendungsbuchung.posting_date,
                Gewinnverwendungsbuchung.id,
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    def list_for_posting_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> tuple[ProfitAppropriationPosting, ...]:
        """Lädt Umsetzungsbuchungen, die im Geschäftsjahr gebucht wurden."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        if not isinstance(fiscal_year, FiscalYear):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        models = (
            self._session.query(
                Gewinnverwendungsbuchung
            )
            .join(
                Buchungszeile,
                Gewinnverwendungsbuchung.buchungszeile_id
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
                Gewinnverwendungsbuchung.posting_date,
                Gewinnverwendungsbuchung.id,
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    @staticmethod
    def _to_domain(
        model: Gewinnverwendungsbuchung,
    ) -> ProfitAppropriationPosting:
        """Überführt ein Persistenzmodell ins Domainmodell."""

        return ProfitAppropriationPosting(
            posting_id=UUID(
                model.posting_id
            ),
            source_fiscal_year_end=(
                model.quell_wirtschaftsjahr.end_date
            ),
            posting_date=model.posting_date,
            amount=model.amount,
            booking_id=UUID(
                model.buchungszeile.buchung.booking_id
            ),
            posting_type=ProfitAppropriationPostingType(
                model.posting_type
            ),
        )
