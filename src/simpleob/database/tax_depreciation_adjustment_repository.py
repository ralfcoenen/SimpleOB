"""Repository für steuerliche AfA-Abweichungen."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import (
    Anlageabschreibung,
    SteuerlicheAfaAbweichung,
)
from simpleob.domain.money import to_decimal
from simpleob.domain.tax_depreciation_adjustment import (
    TaxDepreciationAdjustment,
)


class TaxDepreciationAdjustmentRepository:
    """Speichert und lädt steuerliche AfA-Abweichungen."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def save(
        self,
        *,
        depreciation_id: UUID,
        tax_amount: Decimal,
        commit: bool = True,
    ) -> TaxDepreciationAdjustment | None:
        """
        Speichert, aktualisiert oder entfernt eine AfA-Abweichung.

        Entspricht die steuerliche AfA der handelsrechtlichen AfA,
        wird kein Abweichungsdatensatz gespeichert.
        """

        if not isinstance(
            depreciation_id,
            UUID,
        ):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        tax_amount = to_decimal(
            tax_amount
        )

        if tax_amount < Decimal("0.00"):
            raise ValueError(
                "tax_amount must not be negative"
            )

        query = (
            self._session.query(Anlageabschreibung)
            .filter(
                Anlageabschreibung.depreciation_id
                == str(depreciation_id)
            )
        )

        if self._session.bind.dialect.name == "postgresql":
            try:
                self._session.execute(
                    text(
                        "SELECT set_config("
                        "'lock_timeout', '3000ms', true)"
                    )
                )

                depreciation = (
                    query
                    .with_for_update()
                    .populate_existing()
                    .one_or_none()
                )
            except OperationalError as exc:
                self._session.rollback()

                if (
                    getattr(exc.orig, "sqlstate", None)
                    == "55P03"
                ):
                    raise DatabaseLockError(
                        "Steuerliche AfA-Anpassung momentan gesperrt.\n\n"
                        "Ein anderer Benutzer bearbeitet derzeit "
                        "diese Anlagenabschreibung.\n\n"
                        "Es wurden keine Änderungen gespeichert.\n\n"
                        "Bitte versuchen Sie es in einigen Sekunden erneut."
                    ) from exc

                raise
        else:
            depreciation = query.one_or_none()

        if depreciation is None:
            raise ValueError(
                "Anlagenabschreibung ist nicht vorhanden"
            )

        commercial_amount = to_decimal(
            depreciation.amount
        )

        model = (
            self._session.query(
                SteuerlicheAfaAbweichung
            )
            .filter(
                SteuerlicheAfaAbweichung.anlageabschreibung_id
                == depreciation.id
            )
            .one_or_none()
        )

        if tax_amount == commercial_amount:
            if model is not None:
                self._session.delete(model)

            if commit:
                self._session.commit()

            return None

        adjustment = TaxDepreciationAdjustment(
            depreciation_id=depreciation_id,
            commercial_amount=commercial_amount,
            tax_amount=tax_amount,
        )

        if model is None:
            model = SteuerlicheAfaAbweichung(
                anlageabschreibung_id=depreciation.id,
                tax_amount=adjustment.tax_amount,
            )
            self._session.add(model)
        else:
            model.tax_amount = adjustment.tax_amount

        if commit:
            self._session.commit()

        return adjustment

    def get_for_depreciation(
        self,
        depreciation_id: UUID,
    ) -> TaxDepreciationAdjustment | None:
        """Lädt die AfA-Abweichung einer bestätigten Abschreibung."""

        if not isinstance(
            depreciation_id,
            UUID,
        ):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        model = (
            self._session.query(
                SteuerlicheAfaAbweichung
            )
            .join(
                Anlageabschreibung,
                SteuerlicheAfaAbweichung.anlageabschreibung_id
                == Anlageabschreibung.id,
            )
            .filter(
                Anlageabschreibung.depreciation_id
                == str(depreciation_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    @staticmethod
    def _to_domain(
        model: SteuerlicheAfaAbweichung,
    ) -> TaxDepreciationAdjustment:
        """Überführt das Persistenzmodell ins Domainmodell."""

        depreciation = model.anlageabschreibung

        return TaxDepreciationAdjustment(
            depreciation_id=UUID(
                depreciation.depreciation_id
            ),
            commercial_amount=depreciation.amount,
            tax_amount=model.tax_amount,
        )
