"""Repository für jahresbezogene BVV-Daten."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    BvvJahresdaten,
    Mandant,
    Wirtschaftsjahr,
)
from openbilanz.domain.bvv_annual_data import (
    BvvAnnualData,
)
from openbilanz.domain.fiscal_year import FiscalYear


class BvvAnnualDataRepository:
    """Speichert und lädt jahresbezogene BVV-Daten."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def save_for_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        data: BvvAnnualData,
        commit: bool = True,
    ) -> BvvAnnualData:
        """Speichert oder aktualisiert die BVV-Daten eines Geschäftsjahres."""

        if not isinstance(
            company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        if not isinstance(
            data,
            BvvAnnualData,
        ):
            raise TypeError(
                "data must be a BvvAnnualData"
            )

        fiscal_year_model = self._get_fiscal_year_model(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

        model = (
            self._session.query(
                BvvJahresdaten
            )
            .filter(
                BvvJahresdaten.wirtschaftsjahr_id
                == fiscal_year_model.id
            )
            .one_or_none()
        )

        if model is None:
            model = BvvJahresdaten(
                wirtschaftsjahr_id=fiscal_year_model.id,
                previous_hgb_equity=(
                    data.previous_hgb_equity
                ),
                contribution=data.contribution,
                withdrawal_distribution=(
                    data.withdrawal_distribution
                ),
            )
            self._session.add(model)
        else:
            model.previous_hgb_equity = (
                data.previous_hgb_equity
            )
            model.contribution = data.contribution
            model.withdrawal_distribution = (
                data.withdrawal_distribution
            )

        if commit:
            self._session.commit()

        return data

    def get_for_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> BvvAnnualData | None:
        """Lädt die BVV-Daten eines Geschäftsjahres."""

        if not isinstance(
            company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        fiscal_year_model = self._get_fiscal_year_model(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

        model = (
            self._session.query(
                BvvJahresdaten
            )
            .filter(
                BvvJahresdaten.wirtschaftsjahr_id
                == fiscal_year_model.id
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def _get_fiscal_year_model(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> Wirtschaftsjahr:
        """Lädt das persistierte Geschäftsjahr eines Mandanten."""

        model = (
            self._session.query(
                Wirtschaftsjahr
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
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Geschäftsjahr ist nicht vorhanden"
            )

        return model

    @staticmethod
    def _to_domain(
        model: BvvJahresdaten,
    ) -> BvvAnnualData:
        """Überführt das Persistenzmodell ins Domainmodell."""

        return BvvAnnualData(
            previous_hgb_equity=(
                model.previous_hgb_equity
            ),
            contribution=model.contribution,
            withdrawal_distribution=(
                model.withdrawal_distribution
            ),
        )
