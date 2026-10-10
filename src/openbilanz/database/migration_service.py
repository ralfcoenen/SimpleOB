"""Alembic-Migrationen für die SimpleOB-Datenbank."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from openbilanz.core.config import ApplicationConfig

LEGACY_SCHEMA_REVISION = "f65c37865e28"

LEGACY_SCHEMA = {
    "anlageabschreibungen": {
        "id": (False, True),
        "depreciation_id": (False, False),
        "anlagegut_id": (False, False),
        "wirtschaftsjahr_id": (False, False),
        "buchungszeile_id": (False, False),
        "depreciation_date": (False, False),
        "amount": (False, False),
        "depreciation_kind": (False, False),
        "source": (False, False),
    },
    "anlagebewegungen": {
        "id": (False, True),
        "movement_id": (False, False),
        "anlagegut_id": (False, False),
        "wirtschaftsjahr_id": (False, False),
        "buchungszeile_id": (False, False),
        "movement_date": (False, False),
        "amount": (False, False),
        "movement_type": (False, False),
        "reversed_movement_id": (True, False),
    },
    "anlagegueter": {
        "id": (False, True),
        "fixed_asset_id": (False, False),
        "mandant_id": (False, False),
        "asset_code": (False, False),
        "description": (False, False),
        "position_code": (False, False),
        "acquisition_date": (False, False),
        "acquisition_cost": (False, False),
        "depreciation_start_date": (False, False),
        "useful_life_months": (False, False),
        "status": (False, False),
        "disposal_date": (True, False),
        "asset_account_number": (False, False),
        "depreciation_expense_account_number": (False, False),
    },
    "buchungen": {
        "id": (False, True),
        "booking_id": (False, False),
        "wirtschaftsjahr_id": (False, False),
        "booking_date": (False, False),
        "voucher_no": (True, False),
        "description": (True, False),
        "booking_type": (False, False),
        "reversal_of_booking_id": (True, False),
    },
    "buchungszeilen": {
        "id": (False, True),
        "buchung_id": (False, False),
        "position": (False, False),
        "account_number": (False, False),
        "side": (False, False),
        "amount": (False, False),
    },
    "eigenkapitaleinlagen": {
        "id": (False, True),
        "buchungszeile_id": (False, False),
    },
    "gesellschafter": {
        "id": (False, True),
        "shareholder_id": (False, False),
        "mandant_id": (False, False),
        "shareholder_number": (False, False),
        "name": (False, False),
        "first_name": (False, False),
        "legal_status": (False, False),
        "share_numerator": (False, False),
        "share_denominator": (False, False),
        "tax_number": (False, False),
        "tax_number_federal_state": (False, False),
        "tax_id": (False, False),
        "wid": (False, False),
    },
    "gewinnverwendungs_jahresdaten": {
        "id": (False, True),
        "wirtschaftsjahr_id": (False, False),
        "statutory_reserve_addition": (False, False),
        "other_revenue_reserves_addition": (False, False),
        "statutory_reserve_release": (False, False),
        "other_revenue_reserves_release": (False, False),
        "distribution": (False, False),
        "profit_loss_carryforward": (False, False),
    },
    "gewinnverwendungsbuchungen": {
        "id": (False, True),
        "posting_id": (False, False),
        "quell_wirtschaftsjahr_id": (False, False),
        "buchungszeile_id": (False, False),
        "posting_date": (False, False),
        "amount": (False, False),
        "posting_type": (False, False),
    },
    "konten": {
        "id": (False, True),
        "mandant_id": (False, False),
        "account_number": (False, False),
        "name": (False, False),
        "account_type": (False, False),
        "is_active": (False, False),
        "debit_position_code": (True, False),
        "credit_position_code": (True, False),
    },
    "konten_taxonomie_zuordnungen": {
        "id": (False, True),
        "mandant_id": (False, False),
        "account_number": (False, False),
        "taxonomy_version": (False, False),
        "concept_name": (False, False),
    },
    "kontenrahmen_konfiguration": {
        "id": (False, True),
        "mandant_id": (False, False),
        "opening_balance_account": (False, False),
        "income_summary_account": (False, False),
        "profit_account": (False, False),
        "loss_account": (False, False),
        "profit_loss_carryforward_account": (False, False),
        "statutory_reserve_account": (False, False),
        "other_revenue_reserves_account": (False, False),
        "distribution_liability_account": (False, False),
        "depreciation_expense_account": (False, False),
        "fixed_asset_disposal_gain_account": (False, False),
        "fixed_asset_disposal_loss_account": (False, False),
        "input_tax_7": (False, False),
        "input_tax_19": (False, False),
        "output_tax_7": (False, False),
        "output_tax_19": (False, False),
    },
    "kontenrollen": {
        "id": (False, True),
        "mandant_id": (False, False),
        "role": (False, False),
        "account_number": (False, False),
    },
    "mandanten": {
        "id": (False, True),
        "company_id": (False, False),
        "name": (False, False),
        "rechtsform": (True, False),
        "steuernummer": (True, False),
        "finanzamt": (True, False),
        "steuer_id": (True, False),
        "wirtschafts_id": (True, False),
        "bf4": (True, False),
        "strasse": (True, False),
        "hausnummer": (True, False),
        "plz": (True, False),
        "ort": (True, False),
        "land": (True, False),
        "bundesland": (True, False),
        "geschaeftstaetigkeit": (True, False),
    },
    "steuerliche_afa_abweichungen": {
        "id": (False, True),
        "anlageabschreibung_id": (False, False),
        "tax_amount": (False, False),
    },
    "wirtschaftsjahre": {
        "id": (False, True),
        "mandant_id": (False, False),
        "start_date": (False, False),
        "end_date": (False, False),
        "status": (False, False),
        "opening_source_id": (True, False),
    },
}

LEGACY_FOREIGN_KEYS = {
    ("anlageabschreibungen", "anlagegut_id", "anlagegueter", "id"),
    ("anlageabschreibungen", "buchungszeile_id", "buchungszeilen", "id"),
    ("anlageabschreibungen", "wirtschaftsjahr_id", "wirtschaftsjahre", "id"),
    ("anlagebewegungen", "anlagegut_id", "anlagegueter", "id"),
    ("anlagebewegungen", "buchungszeile_id", "buchungszeilen", "id"),
    ("anlagebewegungen", "reversed_movement_id", "anlagebewegungen", "id"),
    ("anlagebewegungen", "wirtschaftsjahr_id", "wirtschaftsjahre", "id"),
    ("anlagegueter", "mandant_id", "mandanten", "id"),
    ("buchungen", "wirtschaftsjahr_id", "wirtschaftsjahre", "id"),
    ("buchungszeilen", "buchung_id", "buchungen", "id"),
    ("eigenkapitaleinlagen", "buchungszeile_id", "buchungszeilen", "id"),
    ("gesellschafter", "mandant_id", "mandanten", "id"),
    (
        "gewinnverwendungs_jahresdaten",
        "wirtschaftsjahr_id",
        "wirtschaftsjahre",
        "id",
    ),
    (
        "gewinnverwendungsbuchungen",
        "buchungszeile_id",
        "buchungszeilen",
        "id",
    ),
    (
        "gewinnverwendungsbuchungen",
        "quell_wirtschaftsjahr_id",
        "wirtschaftsjahre",
        "id",
    ),
    ("konten", "mandant_id", "mandanten", "id"),
    ("konten_taxonomie_zuordnungen", "mandant_id", "mandanten", "id"),
    ("kontenrahmen_konfiguration", "mandant_id", "mandanten", "id"),
    ("kontenrollen", "mandant_id", "mandanten", "id"),
    (
        "steuerliche_afa_abweichungen",
        "anlageabschreibung_id",
        "anlageabschreibungen",
        "id",
    ),
    ("wirtschaftsjahre", "mandant_id", "mandanten", "id"),
    ("wirtschaftsjahre", "opening_source_id", "wirtschaftsjahre", "id"),
}

LEGACY_UNIQUES = {
    ("anlageabschreibungen", ("depreciation_id",)),
    ("anlageabschreibungen", ("buchungszeile_id",)),
    ("anlagebewegungen", ("buchungszeile_id",)),
    ("anlagebewegungen", ("reversed_movement_id",)),
    ("anlagebewegungen", ("movement_id",)),
    ("anlagegueter", ("fixed_asset_id",)),
    ("anlagegueter", ("mandant_id", "asset_code")),
    ("buchungen", ("booking_id",)),
    ("eigenkapitaleinlagen", ("buchungszeile_id",)),
    ("gesellschafter", ("mandant_id", "shareholder_number")),
    ("gesellschafter", ("shareholder_id",)),
    ("gewinnverwendungs_jahresdaten", ("wirtschaftsjahr_id",)),
    ("gewinnverwendungsbuchungen", ("posting_id",)),
    ("gewinnverwendungsbuchungen", ("buchungszeile_id",)),
    ("konten", ("mandant_id", "account_number")),
    (
        "konten_taxonomie_zuordnungen",
        ("mandant_id", "account_number", "taxonomy_version"),
    ),
    ("kontenrahmen_konfiguration", ("mandant_id",)),
    ("kontenrollen", ("mandant_id", "account_number")),
    ("mandanten", ("company_id",)),
    ("steuerliche_afa_abweichungen", ("anlageabschreibung_id",)),
}


class DatabaseMigrationService:
    """Führt die Alembic-Migrationen einer SimpleOB-Datenbank aus."""

    def __init__(
        self,
        *,
        application_config: ApplicationConfig,
    ) -> None:
        self._application_config = application_config

    def upgrade_to_head(self) -> None:
        """Bringt die konfigurierte Datenbank sicher auf Alembic-Head."""

        alembic_config = self._create_alembic_config()

        database_url = make_url(
            self._application_config.database_url
        )

        is_sqlite = database_url.get_backend_name() == "sqlite"
        is_postgresql = (
            database_url.get_backend_name() == "postgresql"
        )

        if not (is_sqlite or is_postgresql):
            raise RuntimeError(
                "Nicht unterstütztes Datenbanksystem."
            )

        if is_sqlite:
            database_file = self._application_config.database_file

            if not database_file.exists():
                command.upgrade(
                    alembic_config,
                    "head",
                )
                return

        engine = create_engine(
            self._application_config.database_url
        )

        current_revision: str | None = None
        is_legacy_database = False

        try:
            inspector = inspect(engine)
            table_names = set(
                inspector.get_table_names()
            )

            if not table_names:
                command.upgrade(
                    alembic_config,
                    "head",
                )
                return

            if "alembic_version" in table_names:
                with engine.connect() as connection:
                    migration_context = (
                        MigrationContext.configure(connection)
                    )

                    current_revision = (
                        migration_context.get_current_revision()
                    )
            else:
                if not is_sqlite:
                    raise RuntimeError(
                        "Die PostgreSQL-Datenbank enthält bereits "
                        "Tabellen, aber keine Alembic-Versionsinformation. "
                        "Die Datenbank wurde nicht verändert."
                    )

                if not self._matches_legacy_schema(
                    inspector=inspector,
                    table_names=table_names,
                ):
                    raise RuntimeError(
                        "Die vorhandene SimpleOB-Datenbank besitzt "
                        "keine Alembic-Versionsinformation und entspricht "
                        "nicht dem bekannten Legacy-Schema. "
                        "Die Datenbank wurde nicht verändert."
                    )

                is_legacy_database = True

        finally:
            engine.dispose()

        head_revision = self._head_revision(
            alembic_config
        )

        if not is_legacy_database:
            if current_revision == head_revision:
                return

            if is_sqlite:
                self._backup_database()

            command.upgrade(
                alembic_config,
                "head",
            )
            return

        self._backup_database()

        command.stamp(
            alembic_config,
            LEGACY_SCHEMA_REVISION,
        )

        command.upgrade(
            alembic_config,
            "head",
    )

    @staticmethod
    def _head_revision(
        alembic_config: Config,
    ) -> str:
        """Liefert die aktuelle Alembic-Head-Revision."""

        script_directory = ScriptDirectory.from_config(
            alembic_config
        )

        head_revision = script_directory.get_current_head()

        if head_revision is None:
            raise RuntimeError(
                "Für die SimpleOB-Datenbank wurde keine "
                "Alembic-Head-Revision gefunden."
            )

        return head_revision

    def _backup_database(self) -> Path:
        """Sichert die SQLite-Datenbank vor einer Schemaänderung."""

        database_file = self._application_config.database_file

        backup_file = database_file.with_name(
            f"{database_file.stem}"
            "-before-migration"
            f"{database_file.suffix}"
        )

        try:
            with sqlite3.connect(database_file) as source:
                with sqlite3.connect(backup_file) as target:
                    source.backup(target)
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Die SimpleOB-Datenbank konnte vor der "
                "Migration nicht gesichert werden."
            ) from exc

        return backup_file

    @staticmethod
    def _matches_legacy_schema(
        *,
        inspector,
        table_names: set[str],
    ) -> bool:
        expected_table_names = set(
            LEGACY_SCHEMA
        )

        if table_names != expected_table_names:
            return False

        actual_foreign_keys: set[
            tuple[str, str, str, str]
        ] = set()

        actual_uniques: set[
            tuple[str, tuple[str, ...]]
        ] = set()

        for table_name, expected_columns in LEGACY_SCHEMA.items():
            actual_columns = {
                column["name"]: (
                    bool(column["nullable"]),
                    bool(column.get("primary_key")),
                )
                for column in inspector.get_columns(
                    table_name
                )
            }

            if actual_columns != expected_columns:
                return False

            for foreign_key in inspector.get_foreign_keys(
                table_name
            ):
                constrained_columns = tuple(
                    foreign_key["constrained_columns"]
                )
                referred_columns = tuple(
                    foreign_key["referred_columns"]
                )

                if (
                    len(constrained_columns) != 1
                    or len(referred_columns) != 1
                ):
                    return False

                actual_foreign_keys.add(
                    (
                        table_name,
                        constrained_columns[0],
                        foreign_key["referred_table"],
                        referred_columns[0],
                    )
                )

            for unique in inspector.get_unique_constraints(
                table_name
            ):
                column_names = tuple(
                    unique["column_names"]
                )

                actual_uniques.add(
                    (
                        table_name,
                        column_names,
                    )
                )

        if actual_foreign_keys != LEGACY_FOREIGN_KEYS:
            return False

        if actual_uniques != LEGACY_UNIQUES:
            return False

        return True

    def _create_alembic_config(self) -> Config:
        """Erzeugt die Alembic-Konfiguration für die Laufzeitumgebung."""

        resource_root = self._resource_root()

        alembic_ini = resource_root / "alembic.ini"
        migrations_dir = resource_root / "migrations"

        if not alembic_ini.is_file():
            raise RuntimeError(
                "Die Alembic-Konfigurationsdatei wurde nicht gefunden: "
                f"{alembic_ini}"
            )

        if not migrations_dir.is_dir():
            raise RuntimeError(
                "Das Alembic-Migrationsverzeichnis wurde nicht gefunden: "
                f"{migrations_dir}"
            )

        alembic_config = Config(
            str(alembic_ini)
        )

        alembic_config.set_main_option(
            "script_location",
            str(migrations_dir),
        )

        alembic_config.attributes["database_url"] = (
            self._application_config.database_url
        )

        return alembic_config

    @staticmethod
    def _resource_root() -> Path:
        """Liefert das Verzeichnis mit den Alembic-Ressourcen."""

        if getattr(sys, "frozen", False):
            bundle_dir_value = getattr(
                sys,
                "_MEIPASS",
                None,
            )

            if not bundle_dir_value:
                raise RuntimeError(
                    "Das PyInstaller-Ressourcenverzeichnis "
                    "konnte nicht bestimmt werden."
                )

            return Path(bundle_dir_value)

        return Path(__file__).resolve().parents[3]
