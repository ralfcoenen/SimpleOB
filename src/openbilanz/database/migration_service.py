"""Alembic-Migrationen für die OpenBilanz-Anwendungsdatenbank."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from openbilanz.core.config import ApplicationConfig


class MigrationService:
    """Bringt eine OpenBilanz-Datenbank auf den aktuellen Schema-Stand."""

    def __init__(
        self,
        *,
        config: ApplicationConfig,
    ) -> None:
        self._config = config

    def upgrade_to_head(self) -> None:
        """Führt alle ausstehenden Alembic-Migrationen aus."""

        project_root = Path(__file__).resolve().parents[3]

        alembic_config = Config(
            str(project_root / "alembic.ini")
        )

        alembic_config.set_main_option(
            "sqlalchemy.url",
            self._config.database_url,
        )

        alembic_config.set_main_option(
            "script_location",
            str(project_root / "migrations"),
        )

        command.upgrade(
            alembic_config,
            "head",
        )
