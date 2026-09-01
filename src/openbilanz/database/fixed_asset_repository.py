"""Repository für Anlagegüter."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import Anlagegut, Mandant
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)


class FixedAssetRepository:
    """Speichert und lädt Anlagegüter eines Unternehmens."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        fixed_asset: FixedAsset,
        commit: bool = True,
    ) -> None:
        """Speichert ein Anlagegut."""

        if not isinstance(
            fixed_asset,
            FixedAsset,
        ):
            raise TypeError(
                "fixed_asset must be a FixedAsset"
            )

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(fixed_asset.company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        existing_id = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset.fixed_asset_id)
            )
            .one_or_none()
        )

        if existing_id is not None:
            raise ValueError(
                "Das Anlagegut ist bereits vorhanden."
            )

        existing_code = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.mandant_id
                == company_model.id,
                Anlagegut.asset_code
                == fixed_asset.asset_code,
            )
            .one_or_none()
        )

        if existing_code is not None:
            raise ValueError(
                "Die Anlagen-ID ist für dieses "
                "Unternehmen bereits vorhanden."
            )

        model = Anlagegut(
            fixed_asset_id=str(
                fixed_asset.fixed_asset_id
            ),
            mandant_id=company_model.id,
            asset_code=fixed_asset.asset_code,
            description=fixed_asset.description,
            position_code=fixed_asset.position_code,
            asset_account_number=(
                fixed_asset.asset_account_number
            ),
            depreciation_expense_account_number=(
                fixed_asset.depreciation_expense_account_number
            ),
            acquisition_date=(
                fixed_asset.acquisition_date
            ),
            acquisition_cost=(
                fixed_asset.acquisition_cost
            ),
            depreciation_start_date=(
                fixed_asset.depreciation_start_date
            ),
            useful_life_months=(
                fixed_asset.useful_life_months
            ),
            status=fixed_asset.status.value,
            disposal_date=fixed_asset.disposal_date,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def update(
        self,
        *,
        fixed_asset: FixedAsset,
        commit: bool = True,
    ) -> None:
        """Aktualisiert ein vorhandenes Anlagegut."""

        if not isinstance(
            fixed_asset,
            FixedAsset,
        ):
            raise TypeError(
                "fixed_asset must be a FixedAsset"
            )

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id
                == str(fixed_asset.company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset.fixed_asset_id),
                Anlagegut.mandant_id
                == company_model.id,
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        duplicate_code = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.mandant_id
                == company_model.id,
                Anlagegut.asset_code
                == fixed_asset.asset_code,
                Anlagegut.id != model.id,
            )
            .one_or_none()
        )

        if duplicate_code is not None:
            raise ValueError(
                "Die Anlagen-ID ist für dieses "
                "Unternehmen bereits vorhanden."
            )

        model.asset_code = fixed_asset.asset_code
        model.description = fixed_asset.description
        model.position_code = fixed_asset.position_code
        model.asset_account_number = (
            fixed_asset.asset_account_number
        )
        model.depreciation_expense_account_number = (
            fixed_asset.depreciation_expense_account_number
        )
        model.acquisition_date = (
            fixed_asset.acquisition_date
        )
        model.acquisition_cost = (
            fixed_asset.acquisition_cost
        )
        model.depreciation_start_date = (
            fixed_asset.depreciation_start_date
        )
        model.useful_life_months = (
            fixed_asset.useful_life_months
        )
        model.status = fixed_asset.status.value
        model.disposal_date = fixed_asset.disposal_date

        if commit:
            self._session.commit()

    def delete(
        self,
        *,
        fixed_asset_id: UUID,
        commit: bool = True,
    ) -> None:
        """Löscht ein vorhandenes Anlagegut."""

        if not isinstance(
            fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset_id)
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        self._session.delete(model)

        if commit:
            self._session.commit()

    def get(
        self,
        fixed_asset_id: UUID,
    ) -> FixedAsset | None:
        """Lädt ein Anlagegut über seine fachliche ID."""

        if not isinstance(
            fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def list_for_company(
        self,
        company_id: UUID,
    ) -> tuple[FixedAsset, ...]:
        """Lädt alle Anlagegüter eines Unternehmens."""

        if not isinstance(
            company_id,
            UUID,
        ):
            raise TypeError(
                "company_id must be a UUID"
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

        models = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.mandant_id
                == company_model.id
            )
            .order_by(
                Anlagegut.asset_code,
                Anlagegut.id,
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    @staticmethod
    def _to_domain(
        model: Anlagegut,
    ) -> FixedAsset:
        """Überführt ein Persistenzmodell ins Domainmodell."""

        return FixedAsset(
            fixed_asset_id=UUID(
                model.fixed_asset_id
            ),
            company_id=UUID(
                model.mandant.company_id
            ),
            asset_code=model.asset_code,
            description=model.description,
            position_code=model.position_code,
            asset_account_number=(
                model.asset_account_number
            ),
            depreciation_expense_account_number=(
                model.depreciation_expense_account_number
            ),
            acquisition_date=model.acquisition_date,
            acquisition_cost=model.acquisition_cost,
            depreciation_start_date=(
                model.depreciation_start_date
            ),
            useful_life_months=(
                model.useful_life_months
            ),
            status=FixedAssetStatus(
                model.status
            ),
            disposal_date=model.disposal_date,
        )
