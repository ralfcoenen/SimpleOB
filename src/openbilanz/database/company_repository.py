"""Repository für Unternehmen."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from openbilanz.database.lock_error import DatabaseLockError
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
        *,
        commit: bool = True,
    ) -> None:
        """Speichert ein Unternehmen."""

        model = Mandant(
            company_id=str(company.company_id),
            name=company.name,
        )

        self._session.add(model)

        if commit:
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
        *,
        commit: bool = True,
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

        if commit:
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

    def lock_open_fiscal_year(
        self,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> None:
        """Sperrt ein offenes Geschäftsjahr für die laufende Transaktion."""

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

        is_postgresql = (
            self._session.get_bind().dialect.name == "postgresql"
        )

        if is_postgresql:
            # Gilt nur für die aktuelle Transaktion.
            self._session.execute(
                text(
                    "SELECT set_config("
                    "'lock_timeout', '3000ms', true)"
                )
            )

        query = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id == company_model.id,
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
        )

        if is_postgresql:
            query = (
                query
                .with_for_update(of=Wirtschaftsjahr)
                .populate_existing()
            )

        try:
            fiscal_year_model = query.one_or_none()

        except OperationalError as exc:
            sqlstate = getattr(
                exc.orig,
                "sqlstate",
                None,
            )

            if is_postgresql and sqlstate == "55P03":
                self._session.rollback()

                raise DatabaseLockError(
                    "Geschäftsjahr momentan gesperrt.\n\n"
                    "Ein anderer Benutzer bearbeitet derzeit "
                    "dieses Geschäftsjahr.\n\n"
                    "Ihr Vorgang konnte nicht abgeschlossen "
                    "werden. Es wurden keine Änderungen "
                    "gespeichert.\n\n"
                    "Bitte versuchen Sie es in einigen "
                    "Sekunden erneut."
                ) from exc

            raise

        if fiscal_year_model is None:
            raise ValueError(
                "Geschäftsjahr wurde nicht gefunden."
            )

        if fiscal_year_model.status == FiscalYearStatus.CLOSED.value:
            raise ValueError(
                "Geschäftsjahr ist bereits abgeschlossen."
            )


    def close_fiscal_year(
        self,
        company_id: UUID,
        fiscal_year: FiscalYear,
        *,
        commit: bool = True,
    ) -> None:
        """Schließt ein Geschäftsjahr ab."""

        self.lock_open_fiscal_year(
            company_id,
            fiscal_year,
        )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .join(Mandant)
            .filter(
                Mandant.company_id == str(company_id),
                Wirtschaftsjahr.start_date == fiscal_year.start_date,
                Wirtschaftsjahr.end_date == fiscal_year.end_date,
            )
            .one()
        )

        fiscal_year_model.status = FiscalYearStatus.CLOSED.value

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
            federal_state=model.bundesland or "",
            business=model.geschaeftstaetigkeit or "",
        )

    def save_master_data(
        self,
        master_data: CompanyMasterData,
        *,
        commit: bool = True,
        expected_master_data: CompanyMasterData | None = None,
    ) -> None:
        """Speichert Stammdaten mit optionaler Konfliktprüfung."""

        if (
            expected_master_data is not None
            and expected_master_data.company != master_data.company
        ):
            raise ValueError(
                "Die erwarteten Stammdaten gehören zu einem "
                "anderen Unternehmen."
            )

        query = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(master_data.company.company_id)
            )
        )

        if (
            expected_master_data is not None
            and self._session.bind.dialect.name == "postgresql"
        ):
            try:
                self._session.execute(
                    text(
                        "SELECT set_config("
                        "'lock_timeout', '3000ms', true)"
                    )
                )
                model = (
                    query.with_for_update()
                    .populate_existing()
                    .one_or_none()
                )
            except OperationalError as exc:
                self._session.rollback()
                if getattr(exc.orig, "sqlstate", None) == "55P03":
                    raise DatabaseLockError(
                        "Unternehmensstammdaten momentan gesperrt.\n\n"
                        "Ein anderer Benutzer bearbeitet "
                        "diese Stammdaten.\n\n"
                        "Bitte versuchen Sie es später erneut."
                    ) from exc
                raise
        else:
            model = query.one_or_none()

        if model is None:
            raise ValueError(
                "Unternehmen wurde nicht gefunden."
            )

        if expected_master_data is not None:
            current_master_data = CompanyMasterData(
                company=Company(
                    company_id=UUID(model.company_id),
                    name=model.name,
                ),
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
                federal_state=model.bundesland or "",
                business=model.geschaeftstaetigkeit or "",
            )

            if current_master_data != expected_master_data:
                self._session.rollback()
                raise ValueError(
                    "Die Unternehmensstammdaten wurden "
                    "zwischenzeitlich von einem anderen Benutzer "
                    "geändert.\n\n"
                    "Ihre Änderungen wurden nicht gespeichert. "
                    "Bitte öffnen Sie die Stammdaten erneut."
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
        model.bundesland = (
            master_data.federal_state or None
        )
        model.geschaeftstaetigkeit = (
            master_data.business or None
        )

        if commit:
            self._session.commit()

    def commit(self) -> None:
        """Bestätigt die aktuelle Repository-Transaktion."""

        self._session.commit()

    def rollback(self) -> None:
        """Verwirft die aktuelle Repository-Transaktion."""

        self._session.rollback()
