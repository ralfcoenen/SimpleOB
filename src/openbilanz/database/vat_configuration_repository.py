"""Repository für die umsatzsteuerliche Mandantenkonfiguration."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.models import (
    Mandant,
    UmsatzsteuerKonfiguration,
)
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.domain.vat_taxation_method import (
    VatTaxationMethod,
)
from openbilanz.domain.vat_taxation_type import (
    VatTaxationType,
)


class VatConfigurationRepository:
    """Speichert und lädt die umsatzsteuerliche Konfiguration."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def save(
        self,
        *,
        company_id: UUID,
        configuration: VatConfiguration,
        commit: bool = True,
    ) -> None:
        """Speichert die Umsatzsteuerkonfiguration eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(
            configuration,
            VatConfiguration,
        ):
            raise TypeError(
                "configuration must be a VatConfiguration"
            )

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

        model = (
            self._session.query(
                UmsatzsteuerKonfiguration
            )
            .filter(
                UmsatzsteuerKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            model = UmsatzsteuerKonfiguration(
                mandant_id=company_model.id,
                taxation_type=(
                    configuration.taxation_type.value
                ),
                effective_from=(
                    configuration.effective_from
                ),
                taxation_method=(
                    configuration.taxation_method.value
                ),
            )

            self._session.add(model)
        else:
            model.taxation_type = (
                configuration.taxation_type.value
            )
            model.effective_from = (
                configuration.effective_from
            )
            model.taxation_method = (
                configuration.taxation_method.value
            )

        if commit:
            self._session.commit()

    def load(
        self,
        company_id: UUID,
    ) -> VatConfiguration | None:
        """Lädt die Umsatzsteuerkonfiguration eines Mandanten."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        company_model = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
            .one_or_none()
        )

        if company_model is None:
            return None

        model = (
            self._session.query(
                UmsatzsteuerKonfiguration
            )
            .filter(
                UmsatzsteuerKonfiguration.mandant_id
                == company_model.id
            )
            .one_or_none()
        )

        if model is None:
            return None

        return VatConfiguration(
            taxation_type=VatTaxationType(
                model.taxation_type
            ),
            effective_from=model.effective_from,
            taxation_method=VatTaxationMethod(
                model.taxation_method
            ),
        )
