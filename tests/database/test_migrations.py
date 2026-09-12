"""Tests für die Datenbankmigrationen."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BASELINE_REVISION = "7392d6cc6892"
HEAD_REVISION = "8da4add521ea"


def _alembic_config(
    database_path: Path,
) -> Config:
    """Erzeugt eine Alembic-Konfiguration für eine Testdatenbank."""

    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path}",
    )

    return config


def _current_revision(
    database_path: Path,
) -> str:
    """Liest die aktuelle Alembic-Revision."""

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    try:
        with engine.connect() as connection:
            revision = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()

        return revision
    finally:
        engine.dispose()


def _foreign_key_check(
    database_path: Path,
) -> list[tuple[object, ...]]:
    """Prüft die referenzielle Integrität der SQLite-Datenbank."""

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    try:
        with engine.connect() as connection:
            return list(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).fetchall()
            )
    finally:
        engine.dispose()


def test_migrations_upgrade_from_baseline_to_head(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Die Migrationen ergänzen das aktuelle Schema korrekt."""

    database_path = tmp_path / "openbilanz.db"
    database_url = f"sqlite:///{database_path}"

    monkeypatch.setenv(
        "OPENBILANZ_DATABASE_URL",
        database_url,
    )

    config = _alembic_config(
        database_path
    )

    command.upgrade(
        config,
        BASELINE_REVISION,
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        columns_before = {
            column["name"]
            for column in inspector.get_columns(
                "wirtschaftsjahre"
            )
        }

        tables_before = set(
            inspector.get_table_names()
        )

        assert "opening_source_id" not in columns_before
        assert (
            "steuerliche_afa_abweichungen"
            not in tables_before
        )
    finally:
        engine.dispose()

    command.upgrade(
        config,
        "head",
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        columns_after = {
            column["name"]
            for column in inspector.get_columns(
                "wirtschaftsjahre"
            )
        }

        fiscal_year_foreign_keys = (
            inspector.get_foreign_keys(
                "wirtschaftsjahre"
            )
        )

        assert "opening_source_id" in columns_after

        assert any(
            foreign_key["constrained_columns"]
            == ["opening_source_id"]
            and foreign_key["referred_table"]
            == "wirtschaftsjahre"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in fiscal_year_foreign_keys
        )

        assert (
            "steuerliche_afa_abweichungen"
            in inspector.get_table_names()
        )

        adjustment_columns = {
            column["name"]
            for column in inspector.get_columns(
                "steuerliche_afa_abweichungen"
            )
        }

        assert adjustment_columns == {
            "id",
            "anlageabschreibung_id",
            "tax_amount",
        }

        adjustment_foreign_keys = (
            inspector.get_foreign_keys(
                "steuerliche_afa_abweichungen"
            )
        )

        assert any(
            foreign_key["constrained_columns"]
            == ["anlageabschreibung_id"]
            and foreign_key["referred_table"]
            == "anlageabschreibungen"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in adjustment_foreign_keys
        )

        adjustment_unique_constraints = (
            inspector.get_unique_constraints(
                "steuerliche_afa_abweichungen"
            )
        )

        assert any(
            constraint["column_names"]
            == ["anlageabschreibung_id"]
            for constraint in adjustment_unique_constraints
        )
    finally:
        engine.dispose()

    assert (
        _current_revision(database_path)
        == HEAD_REVISION
    )
    assert _foreign_key_check(database_path) == []


def test_migrations_downgrade_from_head_to_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Der Downgrade stellt das Baseline-Schema wieder her."""

    database_path = tmp_path / "openbilanz.db"
    database_url = f"sqlite:///{database_path}"

    monkeypatch.setenv(
        "OPENBILANZ_DATABASE_URL",
        database_url,
    )

    config = _alembic_config(
        database_path
    )

    command.upgrade(
        config,
        "head",
    )

    command.downgrade(
        config,
        BASELINE_REVISION,
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        columns = {
            column["name"]
            for column in inspector.get_columns(
                "wirtschaftsjahre"
            )
        }

        foreign_keys = inspector.get_foreign_keys(
            "wirtschaftsjahre"
        )

        assert "opening_source_id" not in columns

        assert not any(
            foreign_key["constrained_columns"]
            == ["opening_source_id"]
            for foreign_key in foreign_keys
        )

        assert any(
            foreign_key["constrained_columns"]
            == ["mandant_id"]
            and foreign_key["referred_table"]
            == "mandanten"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in foreign_keys
        )

        assert (
            "steuerliche_afa_abweichungen"
            not in inspector.get_table_names()
        )
    finally:
        engine.dispose()

    assert (
        _current_revision(database_path)
        == BASELINE_REVISION
    )
    assert _foreign_key_check(database_path) == []
