"""Mandantenlöschung ausschließlich nach verifizierter Sicherung.

Eine eigene Verbindung hält vom ersten Lesen bis zum Commit alle Schreibsperren.
Es gibt keine Wiederholung nach einem Fehler und keinen Commit in Repositories.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from simpleob.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from simpleob.client_transfer.archive import write_verified_client_backup
from simpleob.client_transfer.exporter import ClientTransferExporter
from simpleob.client_transfer.importer import ClientTransferImporter
from simpleob.client_transfer.model import ClientTransfer
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.client_deletion_repository import (
    CapturedClient,
    ClientDeletionRepository,
)
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from simpleob.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import FixedAssetRepository
from simpleob.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from simpleob.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from simpleob.database.shareholder_repository import ShareholderRepository
from simpleob.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)


class ClientDeletionCommitUnknown(RuntimeError):
    """Die Verbindung ging während COMMIT verloren; der Ausgang ist unbekannt."""

    def __init__(self, backup_path: Path) -> None:
        self.backup_path = backup_path
        super().__init__(
            "Der Ausgang des PostgreSQL-Commits ist unbestimmt. Weder Erfolg "
            "noch Rollback sind bestätigt. Nicht erneut löschen; den Bestand "
            f"nach Wiederverbindung prüfen. Mandantensicherung: {backup_path}"
        )


def _transfer_repositories(session: Session) -> dict:
    """Dieselben Repositories wie Export und Import der Oberfläche."""
    return {
        "company_repository": CompanyRepository(session),
        "chart_of_accounts_repository": ChartOfAccountsRepository(session),
        "booking_repository": BookingRepository(session),
        "shareholder_repository": ShareholderRepository(session),
        "fixed_asset_repository": FixedAssetRepository(session),
        "fixed_asset_movement_repository": FixedAssetMovementRepository(session),
        "fixed_asset_depreciation_repository": FixedAssetDepreciationRepository(
            session
        ),
        "tax_depreciation_adjustment_repository": TaxDepreciationAdjustmentRepository(
            session
        ),
        "profit_appropriation_annual_data_repository": ProfitAppropriationAnnualDataRepository(
            session
        ),
        "profit_appropriation_posting_repository": ProfitAppropriationPostingRepository(
            session
        ),
        "equity_contribution_repository": EquityContributionRepository(session),
    }


class ClientDeletionService:
    """Sichert und löscht einen Mandanten in einer geschützten Transaktion."""

    def __init__(
        self,
        *,
        engine: Engine,
        position_provider: FinancialStatementPositionProvider,
    ) -> None:
        self._engine = engine
        self._position_provider = position_provider

    def delete(
        self, *, company_id: UUID, expected_name: str, backup_path: Path
    ) -> Path:
        if not isinstance(company_id, UUID):
            raise TypeError("company_id must be a UUID")
        backup_path = Path(backup_path).absolute()
        dialect = self._engine.dialect.name
        if dialect not in ("sqlite", "postgresql"):
            raise ValueError("Mandantenlöschung unterstützt nur SQLite und PostgreSQL.")

        with self._engine.connect() as connection:
            if dialect == "sqlite":
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                    raise ValueError(
                        "SQLite-Fremdschlüsselprüfung konnte nicht aktiviert werden."
                    )
                connection.commit()  # Nur PRAGMA, noch keine Bestandsabfrage.
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                connection = connection.execution_options(
                    isolation_level="READ COMMITTED"
                )
                connection.begin()
            try:
                repository = ClientDeletionRepository(connection)
                repository.lock_and_check_schema()
                before = repository.capture(company_id)
                company = before["mandanten"]
                if len(company) != 1 or company[0]["name"] != expected_name:
                    raise ValueError(
                        "Der ausgewählte Mandant fehlt oder sein Name hat sich geändert."
                    )

                # Session beteiligt sich an der externen Transaktion, besitzt sie nicht.
                with Session(
                    bind=connection, join_transaction_mode="rollback_only"
                ) as session:
                    transfer = ClientTransferExporter(
                        **_transfer_repositories(session)
                    ).export(
                        company_id=company_id,
                        position_provider=self._position_provider,
                    )
                    self._verify_complete_restore(transfer, before)
                    write_verified_client_backup(backup_path, transfer)
                    repository.delete_captured(before)
                    repository.check_deleted(before)

                try:
                    connection.commit()
                except BaseException as exc:
                    # Nur ausdrücklich bestätigte Transaktionsabbrüche erlauben
                    # eine Rollback-Aussage. Auch eine Unterbrechung während COMMIT
                    # kann nach erfolgreichem Server-Commit auftreten.
                    state = getattr(getattr(exc, "orig", None), "sqlstate", None)
                    confirmed_abort = (
                        isinstance(exc, DBAPIError)
                        and not exc.connection_invalidated
                        and state is not None
                        and state[:2] in {"23", "25", "40"}
                        and state != "40003"
                    )
                    if dialect == "postgresql" and not confirmed_abort:
                        connection.invalidate()
                        raise ClientDeletionCommitUnknown(backup_path) from exc
                    raise
            except ClientDeletionCommitUnknown:
                raise
            except BaseException:
                connection.rollback()
                raise
        return backup_path

    def _verify_complete_restore(
        self, transfer: ClientTransfer, before: CapturedClient
    ) -> None:
        """Vergleicht jede fachliche Spalte und FK-Beziehung mit einer Rücksicherung.

        Nur interne Primärschlüssel werden abstrahiert. So werden auch beim
        Export normalisierte Werte und fehlende Datensätze vor der Löschung erkannt.
        Die Quelldatenbank bleibt dabei unverändert.
        """
        probe = create_engine("sqlite:///:memory:")

        @event.listens_for(probe, "connect")
        def foreign_keys(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        try:
            Base.metadata.create_all(probe)
            with Session(probe) as session:
                ClientTransferImporter(
                    **_transfer_repositories(session)
                ).import_transfer(
                    transfer=transfer,
                    position_provider=self._position_provider,
                )
            with probe.connect() as connection:
                after = ClientDeletionRepository(connection).capture(
                    transfer.client.company_id
                )
            if ClientDeletionRepository.canonical(
                before
            ) != ClientDeletionRepository.canonical(after):
                raise ValueError(
                    "Die Mandantensicherung bildet nicht alle gespeicherten Werte "
                    "und Beziehungen verlustfrei ab. Es wird nichts gelöscht."
                )
        finally:
            probe.dispose()
