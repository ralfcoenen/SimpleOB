"""Repository für bestätigte Anlagenabschreibungen."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Anlageabschreibung,
    Anlagegut,
    Buchung,
    Buchungszeile,
    Wirtschaftsjahr,
)
from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)


class FixedAssetDepreciationRepository:
    """Speichert und lädt bestätigte Anlagenabschreibungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        depreciation: FixedAssetDepreciation,
        booking_line_position: int,
        commit: bool = True,
    ) -> None:
        """Speichert eine bestätigte Anlagenabschreibung."""

        if not isinstance(
            depreciation,
            FixedAssetDepreciation,
        ):
            raise TypeError(
                "depreciation must be a "
                "FixedAssetDepreciation"
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

        asset_model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(depreciation.fixed_asset_id)
            )
            .one_or_none()
        )

        if asset_model is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        fiscal_year_model = (
            self._session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id
                == asset_model.mandant_id,
                Wirtschaftsjahr.end_date
                == depreciation.fiscal_year_end,
            )
            .one_or_none()
        )

        if fiscal_year_model is None:
            raise ValueError(
                "Das Geschäftsjahr ist nicht vorhanden."
            )

        booking_model = (
            self._session.query(Buchung)
            .filter(
                Buchung.booking_id
                == str(depreciation.booking_id),
                Buchung.wirtschaftsjahr_id
                == fiscal_year_model.id,
            )
            .one_or_none()
        )

        if booking_model is None:
            raise ValueError(
                "Die Abschreibungsbuchung ist nicht vorhanden."
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

        if (
            booking_line_model.amount
            != depreciation.amount
        ):
            raise ValueError(
                "Der Betrag der Buchungszeile stimmt "
                "nicht mit der Abschreibung überein."
            )

        existing_depreciation = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.depreciation_id
                == str(depreciation.depreciation_id)
            )
            .one_or_none()
        )

        if existing_depreciation is not None:
            raise ValueError(
                "Die Abschreibung ist bereits vorhanden."
            )

        existing_booking_line = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.buchungszeile_id
                == booking_line_model.id
            )
            .one_or_none()
        )

        if existing_booking_line is not None:
            raise ValueError(
                "Die Buchungszeile ist bereits einer "
                "Anlagenabschreibung zugeordnet."
            )

        model = Anlageabschreibung(
            depreciation_id=str(
                depreciation.depreciation_id
            ),
            anlagegut_id=asset_model.id,
            wirtschaftsjahr_id=fiscal_year_model.id,
            buchungszeile_id=booking_line_model.id,
            depreciation_date=(
                depreciation.depreciation_date
            ),
            amount=depreciation.amount,
            depreciation_kind=depreciation.kind.value,
            source=depreciation.source.value,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def get(
        self,
        depreciation_id: UUID,
    ) -> FixedAssetDepreciation | None:
        """Lädt eine Abschreibung über ihre fachliche ID."""

        if not isinstance(
            depreciation_id,
            UUID,
        ):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        model = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.depreciation_id
                == str(depreciation_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def list_for_fixed_asset(
        self,
        fixed_asset_id: UUID,
    ) -> tuple[FixedAssetDepreciation, ...]:
        """Lädt alle Abschreibungen eines Anlageguts."""

        if not isinstance(
            fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        asset_model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset_id)
            )
            .one_or_none()
        )

        if asset_model is None:
            return ()

        models = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.anlagegut_id
                == asset_model.id
            )
            .order_by(
                Anlageabschreibung.depreciation_date,
                Anlageabschreibung.id,
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    def list_with_positions_for_fixed_asset(
        self,
        fixed_asset_id: UUID,
    ) -> tuple[
        tuple[FixedAssetDepreciation, int],
        ...,
    ]:
        """Lädt Abschreibungen samt Buchungszeilenposition."""

        if not isinstance(
            fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        asset_model = (
            self._session.query(Anlagegut)
            .filter(
                Anlagegut.fixed_asset_id
                == str(fixed_asset_id)
            )
            .one_or_none()
        )

        if asset_model is None:
            return ()

        models = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.anlagegut_id
                == asset_model.id
            )
            .order_by(
                Anlageabschreibung.depreciation_date,
                Anlageabschreibung.id,
            )
            .all()
        )

        return tuple(
            (
                self._to_domain(model),
                model.buchungszeile.position,
            )
            for model in models
        )

    @staticmethod
    def _to_domain(
        model: Anlageabschreibung,
    ) -> FixedAssetDepreciation:
        """Überführt ein Persistenzmodell ins Domainmodell."""

        return FixedAssetDepreciation(
            depreciation_id=UUID(
                model.depreciation_id
            ),
            fixed_asset_id=UUID(
                model.anlagegut.fixed_asset_id
            ),
            fiscal_year_end=(
                model.wirtschaftsjahr.end_date
            ),
            depreciation_date=(
                model.depreciation_date
            ),
            amount=model.amount,
            booking_id=UUID(
                model.buchungszeile.buchung.booking_id
            ),
            kind=DepreciationKind(
                model.depreciation_kind
            ),
            source=DepreciationSource(
                model.source
            ),
        )
