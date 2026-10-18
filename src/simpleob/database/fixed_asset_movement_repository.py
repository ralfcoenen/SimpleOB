"""Repository für buchungswirksame Anlagenbewegungen."""

from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.models import (
    Anlagebewegung,
    Anlagegut,
    Buchung,
    Buchungszeile,
    Wirtschaftsjahr,
)
from simpleob.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)


class FixedAssetMovementRepository:
    """Speichert und lädt Anlagenbewegungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def add(
        self,
        *,
        movement: FixedAssetMovement,
        booking_line_position: int,
        commit: bool = True,
    ) -> None:
        """Speichert eine Anlagenbewegung."""

        if not isinstance(
            movement,
            FixedAssetMovement,
        ):
            raise TypeError(
                "movement must be a FixedAssetMovement"
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
                == str(movement.fixed_asset_id)
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
                == movement.fiscal_year_end,
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
                == str(movement.booking_id),
                Buchung.wirtschaftsjahr_id
                == fiscal_year_model.id,
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
                == booking_line_position,
            )
            .one_or_none()
        )

        if booking_line_model is None:
            raise ValueError(
                "Die Buchungszeile ist nicht vorhanden."
            )

        existing_movement = (
            self._session.query(Anlagebewegung)
            .filter(
                Anlagebewegung.movement_id
                == str(movement.movement_id)
            )
            .one_or_none()
        )

        if existing_movement is not None:
            raise ValueError(
                "Die Anlagenbewegung ist bereits vorhanden."
            )

        existing_booking_line = (
            self._session.query(Anlagebewegung)
            .filter(
                Anlagebewegung.buchungszeile_id
                == booking_line_model.id
            )
            .one_or_none()
        )

        if existing_booking_line is not None:
            raise ValueError(
                "Die Buchungszeile ist bereits einer "
                "Anlagenbewegung zugeordnet."
            )

        reversed_movement_model = None

        if movement.reversed_movement_id is not None:
            reversed_movement_model = (
                self._session.query(Anlagebewegung)
                .filter(
                    Anlagebewegung.movement_id
                    == str(
                        movement.reversed_movement_id
                    )
                )
                .one_or_none()
            )

            if reversed_movement_model is None:
                raise ValueError(
                    "Die zu stornierende Anlagenbewegung "
                    "ist nicht vorhanden."
                )

            if (
                reversed_movement_model.anlagegut_id
                != asset_model.id
            ):
                raise ValueError(
                    "Die zu stornierende Anlagenbewegung "
                    "gehört zu einem anderen Anlagegut."
                )

            existing_reversal = (
                self._session.query(Anlagebewegung)
                .filter(
                    Anlagebewegung.reversed_movement_id
                    == reversed_movement_model.id
                )
                .one_or_none()
            )

            if existing_reversal is not None:
                raise ValueError(
                    "Die Anlagenbewegung wurde bereits "
                    "storniert."
                )

        amount_may_differ = (
            movement.movement_type
            is FixedAssetMovementType.DISPOSAL
        )

        if (
            movement.movement_type
            is FixedAssetMovementType.REVERSAL
            and reversed_movement_model is not None
            and reversed_movement_model.movement_type
            == FixedAssetMovementType.DISPOSAL.value
        ):
            amount_may_differ = True

        if (
            not amount_may_differ
            and booking_line_model.amount
            != movement.amount
        ):
            raise ValueError(
                "Der Betrag der Buchungszeile stimmt "
                "nicht mit der Anlagenbewegung überein."
            )

        model = Anlagebewegung(
            movement_id=str(
                movement.movement_id
            ),
            anlagegut_id=asset_model.id,
            wirtschaftsjahr_id=fiscal_year_model.id,
            buchungszeile_id=booking_line_model.id,
            movement_date=movement.movement_date,
            amount=movement.amount,
            movement_type=movement.movement_type.value,
            reversed_movement_id=(
                reversed_movement_model.id
                if reversed_movement_model is not None
                else None
            ),
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def get(
        self,
        movement_id: UUID,
    ) -> FixedAssetMovement | None:
        """Lädt eine Anlagenbewegung über ihre fachliche ID."""

        if not isinstance(
            movement_id,
            UUID,
        ):
            raise TypeError(
                "movement_id must be a UUID"
            )

        model = (
            self._session.query(Anlagebewegung)
            .filter(
                Anlagebewegung.movement_id
                == str(movement_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def list_for_booking(
        self,
        booking_id: UUID,
    ) -> tuple[FixedAssetMovement, ...]:
        """Lädt alle Anlagenbewegungen einer Buchung."""

        if not isinstance(
            booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        models = (
            self._session.query(Anlagebewegung)
            .join(Anlagebewegung.buchungszeile)
            .join(Buchungszeile.buchung)
            .filter(
                Buchung.booking_id
                == str(booking_id)
            )
            .order_by(
                Anlagebewegung.id
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    def list_with_positions_for_booking(
        self,
        booking_id: UUID,
    ) -> tuple[tuple[FixedAssetMovement, int], ...]:
        """Lädt Anlagenbewegungen samt Buchungszeilenposition."""

        if not isinstance(
            booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        models = (
            self._session.query(Anlagebewegung)
            .join(Anlagebewegung.buchungszeile)
            .join(Buchungszeile.buchung)
            .filter(
                Buchung.booking_id
                == str(booking_id)
            )
            .order_by(
                Anlagebewegung.id
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

    def list_for_fixed_asset(
        self,
        fixed_asset_id: UUID,
    ) -> tuple[FixedAssetMovement, ...]:
        """Lädt alle Anlagenbewegungen eines Anlageguts."""

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
            self._session.query(Anlagebewegung)
            .filter(
                Anlagebewegung.anlagegut_id
                == asset_model.id
            )
            .order_by(
                Anlagebewegung.movement_date,
                Anlagebewegung.id,
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
    ) -> tuple[tuple[FixedAssetMovement, int], ...]:
        """Lädt Anlagenbewegungen samt Buchungszeilenposition."""

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
            self._session.query(Anlagebewegung)
            .filter(
                Anlagebewegung.anlagegut_id
                == asset_model.id
            )
            .order_by(
                Anlagebewegung.movement_date,
                Anlagebewegung.id,
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
        model: Anlagebewegung,
    ) -> FixedAssetMovement:
        """Überführt ein Persistenzmodell ins Domainmodell."""

        return FixedAssetMovement(
            movement_id=UUID(
                model.movement_id
            ),
            fixed_asset_id=UUID(
                model.anlagegut.fixed_asset_id
            ),
            fiscal_year_end=(
                model.wirtschaftsjahr.end_date
            ),
            movement_date=model.movement_date,
            amount=model.amount,
            booking_id=UUID(
                model.buchungszeile.buchung.booking_id
            ),
            movement_type=FixedAssetMovementType(
                model.movement_type
            ),
            reversed_movement_id=(
                UUID(
                    model.reversed_movement.movement_id
                )
                if model.reversed_movement is not None
                else None
            ),
        )
