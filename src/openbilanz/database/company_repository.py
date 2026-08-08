"""Repository für Unternehmen."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import Mandant, Wirtschaftsjahr
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


class CompanyRepository:
    """Speichert und lädt Unternehmen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        company: Company,
    ) -> None:
        """Speichert ein Unternehmen."""

        model = Mandant(
            company_id=str(company.company_id),
            name=company.name,
        )

        self._session.add(model)
        self._session.commit()

    def get(
        self,
        company_id: UUID,
    ) -> Company | None:
        """Lädt ein Unternehmen über seine fachliche ID."""

        model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return Company(
            company_id=UUID(model.company_id),
            name=model.name,
        )
    
    def add_fiscal_year(
        self,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> None:
        """Speichert ein Geschäftsjahr für ein Unternehmen."""

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )
            
        overlapping_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.start_date
                <= fiscal_year.end_date,
                Wirtschaftsjahr.end_date
                >= fiscal_year.start_date,
            )
            .first()
        )

        if overlapping_model is not None:
            raise ValueError(
                "Geschäftsjahr überschneidet sich "
                "mit einem vorhandenen Geschäftsjahr."
            )

        model = Wirtschaftsjahr(
            mandant_id=company_model.id,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
        )

        self._session.add(model)
        self._session.commit()


    def get_fiscal_years(
        self,
        company_id: UUID,
    ) -> tuple[FiscalYear, ...]:
        """Lädt die Geschäftsjahre eines Unternehmens."""

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            return ()

        models = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id
            )
            .order_by(
                Wirtschaftsjahr.start_date
            )
            .all()
        )

        return tuple(
            FiscalYear(
                start_date=model.start_date,
                end_date=model.end_date,
            )
            for model in models
        )
