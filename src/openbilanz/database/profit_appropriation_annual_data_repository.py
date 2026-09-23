"""Repository für jahresbezogene Daten zur Ergebnisverwendung."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    GewinnverwendungsJahresdaten,
    Mandant,
    Wirtschaftsjahr,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)


class ProfitAppropriationAnnualDataRepository:
    """Speichert und lädt jahresbezogene Daten zur Ergebnisverwendung."""

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
        data: ProfitAppropriationAnnualData,
        commit: bool = True,
    ) -> ProfitAppropriationAnnualData:
        """Speichert oder aktualisiert die Ergebnisverwendung."""

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
            ProfitAppropriationAnnualData,
        ):
            raise TypeError(
                "data must be a ProfitAppropriationAnnualData"
            )

        fiscal_year_model = self._get_fiscal_year_model(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

        model = (
            self._session.query(
                GewinnverwendungsJahresdaten
            )
            .filter(
                GewinnverwendungsJahresdaten.wirtschaftsjahr_id
                == fiscal_year_model.id
            )
            .one_or_none()
        )

        if model is None:
            model = GewinnverwendungsJahresdaten(
                wirtschaftsjahr_id=fiscal_year_model.id,
                statutory_reserve_addition=(
                    data.statutory_reserve_addition
                ),
                other_revenue_reserves_addition=(
                    data.other_revenue_reserves_addition
                ),
                statutory_reserve_release=(
                    data.statutory_reserve_release
                ),
                other_revenue_reserves_release=(
                    data.other_revenue_reserves_release
                ),
                distribution=data.distribution,
                profit_loss_carryforward=(
                    data.profit_loss_carryforward
                ),
            )
            self._session.add(model)
        else:
            model.statutory_reserve_addition = (
                data.statutory_reserve_addition
            )
            model.other_revenue_reserves_addition = (
                data.other_revenue_reserves_addition
            )
            model.statutory_reserve_release = (
                data.statutory_reserve_release
            )
            model.other_revenue_reserves_release = (
                data.other_revenue_reserves_release
            )
            model.distribution = data.distribution
            model.profit_loss_carryforward = (
                data.profit_loss_carryforward
            )

        if commit:
            self._session.commit()

        return data

    def get_for_fiscal_year(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
    ) -> ProfitAppropriationAnnualData | None:
        """Lädt die Ergebnisverwendung eines Geschäftsjahres."""

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
                GewinnverwendungsJahresdaten
            )
            .filter(
                GewinnverwendungsJahresdaten.wirtschaftsjahr_id
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
        model: GewinnverwendungsJahresdaten,
    ) -> ProfitAppropriationAnnualData:
        """Überführt das Persistenzmodell ins Domainmodell."""

        return ProfitAppropriationAnnualData(
            statutory_reserve_addition=(
                model.statutory_reserve_addition
            ),
            other_revenue_reserves_addition=(
                model.other_revenue_reserves_addition
            ),
            statutory_reserve_release=(
                model.statutory_reserve_release
            ),
            other_revenue_reserves_release=(
                model.other_revenue_reserves_release
            ),
            distribution=model.distribution,
            profit_loss_carryforward=(
                model.profit_loss_carryforward
            ),
        )
