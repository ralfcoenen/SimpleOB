"""Repository für Gesellschafter."""

from uuid import UUID


from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from simpleob.database.lock_error import DatabaseLockError
from sqlalchemy.orm import Session

from simpleob.database.models import Gesellschafter, Mandant
from simpleob.domain.shareholder import Shareholder


class ShareholderRepository:
    """Speichert und lädt Gesellschafter eines Unternehmens."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def _lock_company(
        self,
        company_id: UUID,
    ) -> Mandant:
        """Sperrt einen Mandanten für Gesellschafteränderungen."""

        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")

        is_postgresql = (
            self._session.get_bind().dialect.name
            == "postgresql"
        )

        if is_postgresql:
            self._session.execute(
                text(
                    "SELECT set_config("
                    "'lock_timeout', '3000ms', true)"
                )
            )

        query = (
            self._session.query(Mandant)
            .filter(
                Mandant.company_id == str(company_id)
            )
        )

        if is_postgresql:
            query = (
                query
                .with_for_update(of=Mandant)
                .populate_existing()
            )

        try:
            company_model = query.one_or_none()

        except OperationalError as exc:
            sqlstate = getattr(
                exc.orig,
                "sqlstate",
                None,
            )

            if is_postgresql and sqlstate == "55P03":
                self._session.rollback()

                raise DatabaseLockError(
                    "Gesellschafterverwaltung momentan gesperrt.\n\n"
                    "Ein anderer Benutzer bearbeitet derzeit "
                    "die Gesellschafter dieses Mandanten.\n\n"
                    "Ihr Vorgang konnte nicht abgeschlossen "
                    "werden. Es wurden keine Änderungen "
                    "gespeichert.\n\n"
                    "Bitte versuchen Sie es in einigen "
                    "Sekunden erneut."
                ) from exc

            raise

        if company_model is None:
            raise ValueError(
                "Das Unternehmen ist nicht vorhanden."
            )

        return company_model

    def add(
        self,
        *,
        shareholder: Shareholder,
        commit: bool = True,
    ) -> None:
        """Speichert einen Gesellschafter."""

        if not isinstance(
            shareholder,
            Shareholder,
        ):
            raise TypeError(
                "shareholder must be a Shareholder"
            )

        company_model = self._lock_company(
            shareholder.company_id
        )

        existing_id = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.shareholder_id
                == str(shareholder.shareholder_id)
            )
            .one_or_none()
        )

        if existing_id is not None:
            raise ValueError(
                "Der Gesellschafter ist bereits vorhanden."
            )

        existing_number = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.mandant_id
                == company_model.id,
                Gesellschafter.shareholder_number
                == shareholder.shareholder_number,
            )
            .one_or_none()
        )

        if existing_number is not None:
            raise ValueError(
                "Die Gesellschafter-ID ist für dieses "
                "Unternehmen bereits vorhanden."
            )

        model = Gesellschafter(
            shareholder_id=str(
                shareholder.shareholder_id
            ),
            mandant_id=company_model.id,
            shareholder_number=(
                shareholder.shareholder_number
            ),
            name=shareholder.name,
            first_name=shareholder.first_name,
            legal_status=shareholder.legal_status,
            share_numerator=(
                shareholder.share_numerator
            ),
            share_denominator=(
                shareholder.share_denominator
            ),
            tax_number=shareholder.tax_number,
            tax_number_federal_state=(
                shareholder.tax_number_federal_state
            ),
            tax_id=shareholder.tax_id,
            wid=shareholder.wid,
        )

        self._session.add(model)

        if commit:
            self._session.commit()

    def update(
        self,
        *,
        shareholder: Shareholder,
        commit: bool = True,
    ) -> None:
        """Aktualisiert einen vorhandenen Gesellschafter."""

        if not isinstance(
            shareholder,
            Shareholder,
        ):
            raise TypeError(
                "shareholder must be a Shareholder"
            )

        company_model = self._lock_company(
            shareholder.company_id
        )

        model = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.shareholder_id
                == str(shareholder.shareholder_id),
                Gesellschafter.mandant_id
                == company_model.id,
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Der Gesellschafter ist nicht vorhanden."
            )

        duplicate_number = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.mandant_id
                == company_model.id,
                Gesellschafter.shareholder_number
                == shareholder.shareholder_number,
                Gesellschafter.id != model.id,
            )
            .one_or_none()
        )

        if duplicate_number is not None:
            raise ValueError(
                "Die Gesellschafter-ID ist für dieses "
                "Unternehmen bereits vorhanden."
            )

        model.shareholder_number = (
            shareholder.shareholder_number
        )
        model.name = shareholder.name
        model.first_name = shareholder.first_name
        model.legal_status = shareholder.legal_status
        model.share_numerator = (
            shareholder.share_numerator
        )
        model.share_denominator = (
            shareholder.share_denominator
        )
        model.tax_number = shareholder.tax_number
        model.tax_number_federal_state = (
            shareholder.tax_number_federal_state
        )
        model.tax_id = shareholder.tax_id
        model.wid = shareholder.wid

        if commit:
            self._session.commit()

    def delete(
        self,
        *,
        shareholder_id: UUID,
        commit: bool = True,
    ) -> None:
        """Löscht einen vorhandenen Gesellschafter."""

        if not isinstance(shareholder_id, UUID):
            raise TypeError(
                "shareholder_id must be a UUID"
            )

        model = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.shareholder_id
                == str(shareholder_id)
            )
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Der Gesellschafter ist nicht vorhanden."
            )

        company_id = UUID(model.mandant.company_id)

        company_model = self._lock_company(
            company_id
        )

        model = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.shareholder_id
                == str(shareholder_id),
                Gesellschafter.mandant_id
                == company_model.id,
            )
            .populate_existing()
            .one_or_none()
        )

        if model is None:
            raise ValueError(
                "Der Gesellschafter ist nicht vorhanden."
            )

        self._session.delete(model)

        if commit:
            self._session.commit()

    def get(
        self,
        shareholder_id: UUID,
    ) -> Shareholder | None:
        """Lädt einen Gesellschafter über seine fachliche ID."""

        if not isinstance(
            shareholder_id,
            UUID,
        ):
            raise TypeError(
                "shareholder_id must be a UUID"
            )

        model = (
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.shareholder_id
                == str(shareholder_id)
            )
            .one_or_none()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def list_for_company(
        self,
        company_id: UUID,
    ) -> tuple[Shareholder, ...]:
        """Lädt alle Gesellschafter eines Unternehmens."""

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
            self._session.query(Gesellschafter)
            .filter(
                Gesellschafter.mandant_id
                == company_model.id
            )
            .order_by(
                Gesellschafter.shareholder_number,
                Gesellschafter.id,
            )
            .all()
        )

        return tuple(
            self._to_domain(model)
            for model in models
        )

    @staticmethod
    def _to_domain(
        model: Gesellschafter,
    ) -> Shareholder:
        """Überführt ein Persistenzmodell ins Domainmodell."""

        return Shareholder(
            shareholder_id=UUID(
                model.shareholder_id
            ),
            company_id=UUID(
                model.mandant.company_id
            ),
            shareholder_number=(
                model.shareholder_number
            ),
            name=model.name,
            first_name=model.first_name,
            legal_status=model.legal_status,
            share_numerator=(
                model.share_numerator
            ),
            share_denominator=(
                model.share_denominator
            ),
            tax_number=model.tax_number,
            tax_number_federal_state=(
                model.tax_number_federal_state
            ),
            tax_id=model.tax_id,
            wid=model.wid,
        )
