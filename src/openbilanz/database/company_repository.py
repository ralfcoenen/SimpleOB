"""Repository für Unternehmen."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import Mandant, Wirtschaftsjahr
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear


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
            status=FiscalYearStatus.OPEN.value,
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
    
    def list_companies(
        self,
    ) -> tuple[Company, ...]:
        """Lädt alle Unternehmen alphabetisch nach Namen."""

        models = (
            self._session.query(Mandant)
            .order_by(
                Mandant.name,
                Mandant.company_id,
            )
            .all()
        )

        return tuple(
            Company(
                company_id=UUID(model.company_id),
                name=model.name,
            )
            for model in models
        )

    def get_managed_fiscal_years(
        self,
        company_id: UUID,
    ) -> tuple[ManagedFiscalYear, ...]:
        """Lädt Geschäftsjahre einschließlich ihres Status."""

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
            ManagedFiscalYear(
                fiscal_year=FiscalYear(
                    start_date=model.start_date,
                    end_date=model.end_date,
                ),
                status=FiscalYearStatus(
                    model.status
                ),
                opening_source=(
                    FiscalYear(
                        start_date=model.opening_source.start_date,
                        end_date=model.opening_source.end_date,
                    )
                    if model.opening_source is not None
                    else None
                ),
            )
            for model in models
        )

    def set_opening_source(
        self,
        company_id: UUID,
        fiscal_year: FiscalYear,
        opening_source: FiscalYear,
        *,
        commit: bool = True,
    ) -> None:
        """Speichert das Herkunftsgeschäftsjahr einer Eröffnung."""

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Unternehmen wurde nicht gefunden."
            )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.start_date
                == fiscal_year.start_date,
                Wirtschaftsjahr.end_date
                == fiscal_year.end_date,
            )
            .one_or_none()
        )

        if fiscal_year_model is None:
            raise ValueError(
                "Geschäftsjahr wurde nicht gefunden."
            )

        opening_source_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.start_date
                == opening_source.start_date,
                Wirtschaftsjahr.end_date
                == opening_source.end_date,
            )
            .one_or_none()
        )

        if opening_source_model is None:
            raise ValueError(
                "Herkunftsgeschäftsjahr wurde nicht gefunden."
            )

        fiscal_year_model.opening_source = (
            opening_source_model
        )

        if commit:
            self._session.commit()

    def close_fiscal_year(
        self,
        company_id: UUID,
        fiscal_year: FiscalYear,
        *,
        commit: bool = True,
    ) -> None:
        """Schließt ein Geschäftsjahr ab."""

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Unternehmen wurde nicht gefunden."
            )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == company_model.id,
                Wirtschaftsjahr.start_date
                == fiscal_year.start_date,
                Wirtschaftsjahr.end_date
                == fiscal_year.end_date,
            )
            .one_or_none()
        )

        if fiscal_year_model is None:
            raise ValueError(
                "Geschäftsjahr wurde nicht gefunden."
            )

        if (
            fiscal_year_model.status
            == FiscalYearStatus.CLOSED.value
        ):
            raise ValueError(
                "Geschäftsjahr ist bereits abgeschlossen."
            )

        fiscal_year_model.status = (
            FiscalYearStatus.CLOSED.value
        )

        if commit:
            self._session.commit()
        
    def get_master_data(
    self,
    company_id: UUID,
) -> CompanyMasterData | None:
        """Lädt die Stammdaten eines Unternehmens."""

        model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        company = Company(
            company_id=UUID(model.company_id),
            name=model.name,
        )

        return CompanyMasterData(
            company=company,
            legal_form=model.rechtsform or "",
            tax_number=model.steuernummer or "",
            tax_office=model.finanzamt or "",
            tax_id=model.steuer_id or "",
            tax_economic_id=model.wirtschafts_id or "",
            bf4=model.bf4 or "",
            street=model.strasse or "",
            house_number=model.hausnummer or "",
            postal_code=model.plz or "",
            city=model.ort or "",
            country=model.land or "",
            business=model.geschaeftstaetigkeit or "",
        ) 
        
    def save_master_data(
        self,
        master_data: CompanyMasterData,
    ) -> None:
        """Speichert die Stammdaten eines Unternehmens."""

        model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(master_data.company.company_id)
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Unternehmen wurde nicht gefunden."
            )

        model.rechtsform = (
            master_data.legal_form or None
        )
        model.steuernummer = (
            master_data.tax_number or None
        )
        model.finanzamt = (
            master_data.tax_office or None
        )
        model.steuer_id = (
            master_data.tax_id or None
        )
        model.wirtschafts_id = (
            master_data.tax_economic_id or None
        )
        model.bf4 = (
            master_data.bf4 or None
        )
        model.strasse = (
            master_data.street or None
        )
        model.hausnummer = (
            master_data.house_number or None
        )
        model.plz = (
            master_data.postal_code or None
        )
        model.ort = (
            master_data.city or None
        )
        model.land = (
            master_data.country or None
        )
        model.geschaeftstaetigkeit = (
            master_data.business or None
        )

        self._session.commit()       