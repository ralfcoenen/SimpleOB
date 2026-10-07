"""Tests für die Datenbankmigrationen."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BASELINE_REVISION = "7392d6cc6892"
HEAD_REVISION = "3d5f3f742f56"


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

        booking_columns = {
            column["name"]
            for column in inspector.get_columns(
                "buchungen"
            )
        }

        assert "reversal_of_booking_id" in booking_columns

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

        assert (
            "konten_taxonomie_zuordnungen"
            in inspector.get_table_names()
        )

        taxonomy_mapping_columns = {
            column["name"]
            for column in inspector.get_columns(
                "konten_taxonomie_zuordnungen"
            )
        }

        assert taxonomy_mapping_columns == {
            "id",
            "mandant_id",
            "account_number",
            "taxonomy_version",
            "concept_name",
        }

        taxonomy_mapping_foreign_keys = (
            inspector.get_foreign_keys(
                "konten_taxonomie_zuordnungen"
            )
        )

        assert any(
            foreign_key["constrained_columns"]
            == ["mandant_id"]
            and foreign_key["referred_table"]
            == "mandanten"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in taxonomy_mapping_foreign_keys
        )

        taxonomy_mapping_unique_constraints = (
            inspector.get_unique_constraints(
                "konten_taxonomie_zuordnungen"
            )
        )

        assert any(
            constraint["column_names"]
            == [
                "mandant_id",
                "account_number",
                "taxonomy_version",
            ]
            for constraint
            in taxonomy_mapping_unique_constraints
        )

    finally:
        engine.dispose()

    assert (
        _current_revision(database_path)
        == HEAD_REVISION
    )
    assert _foreign_key_check(database_path) == []


def test_account_taxonomy_mapping_migration_preserves_existing_table(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Eine historisch bereits vorhandene Tabelle bleibt unverändert."""

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
        "f65c37865e28",
    )

    engine = create_engine(
        database_url
    )

    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE konten_taxonomie_zuordnungen (
                    id INTEGER NOT NULL,
                    mandant_id INTEGER NOT NULL,
                    account_number VARCHAR NOT NULL,
                    taxonomy_version VARCHAR NOT NULL,
                    concept_name VARCHAR NOT NULL,
                    PRIMARY KEY (id),
                    FOREIGN KEY(mandant_id)
                        REFERENCES mandanten (id),
                    CONSTRAINT
                        uq_konten_taxonomie_mandant_account_version
                    UNIQUE (
                        mandant_id,
                        account_number,
                        taxonomy_version
                    )
                )
                """
            )

            result = connection.exec_driver_sql(
                """
                INSERT INTO mandanten (
                    company_id,
                    name
                )
                VALUES (
                    'taxonomy-migration-test',
                    'Taxonomy Migration Test UG'
                )
                """
            )

            mandant_id = result.lastrowid

            connection.exec_driver_sql(
                """
                INSERT INTO konten_taxonomie_zuordnungen (
                    mandant_id,
                    account_number,
                    taxonomy_version,
                    concept_name
                )
                VALUES (
                    ?,
                    '1400',
                    '6.9',
                    'bs.ass.currAss.receiv.trade.other'
                )
                """,
                (mandant_id,),
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

        assert (
            "konten_taxonomie_zuordnungen"
            in inspector.get_table_names()
        )

        with engine.connect() as connection:
            mapping = connection.exec_driver_sql(
                """
                SELECT
                    account_number,
                    taxonomy_version,
                    concept_name
                FROM konten_taxonomie_zuordnungen
                """
            ).one()

        assert mapping == (
            "1400",
            "6.9",
            "bs.ass.currAss.receiv.trade.other",
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


def test_profit_appropriation_control_accounts_migration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Die Ergebnisverwendungskonten werden kollisionsschonend ergänzt."""

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
        "d6043facfad4",
    )

    engine = create_engine(
        database_url
    )

    try:
        with engine.begin() as connection:
            result = connection.exec_driver_sql(
                """
                INSERT INTO mandanten (
                    company_id,
                    name
                )
                VALUES (
                    'migration-test-company',
                    'Migration Test UG'
                )
                """
            )

            mandant_id = result.lastrowid

            connection.exec_driver_sql(
                """
                INSERT INTO konten (
                    mandant_id,
                    account_number,
                    name,
                    account_type,
                    is_active,
                    debit_position_code,
                    credit_position_code
                )
                VALUES (
                    ?,
                    '0846',
                    'Individuelles bestehendes Konto',
                    'LIABILITY',
                    0,
                    'INDIVIDUAL.DEBIT',
                    'INDIVIDUAL.CREDIT'
                )
                """,
                (mandant_id,),
            )

            connection.exec_driver_sql(
                """
                INSERT INTO kontenrahmen_konfiguration (
                    mandant_id,
                    opening_balance_account,
                    income_summary_account,
                    profit_account,
                    loss_account,
                    profit_loss_carryforward_account,
                    depreciation_expense_account,
                    fixed_asset_disposal_gain_account,
                    fixed_asset_disposal_loss_account,
                    input_tax_7,
                    input_tax_19,
                    output_tax_7,
                    output_tax_19
                )
                VALUES (
                    ?,
                    '9000',
                    '8990',
                    '8020',
                    '8021',
                    '2970',
                    '4830',
                    '8500',
                    '4900',
                    '1571',
                    '1576',
                    '1771',
                    '1776'
                )
                """,
                (mandant_id,),
            )
    finally:
        engine.dispose()

    command.upgrade(
        config,
        "36fe523b87a4",
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        configuration_columns = {
            column["name"]
            for column in inspector.get_columns(
                "kontenrahmen_konfiguration"
            )
        }

        assert "statutory_reserve_account" in configuration_columns
        assert (
            "other_revenue_reserves_account"
            in configuration_columns
        )
        assert (
            "distribution_liability_account"
            in configuration_columns
        )

        with engine.connect() as connection:
            configuration = connection.exec_driver_sql(
                """
                SELECT
                    statutory_reserve_account,
                    other_revenue_reserves_account,
                    distribution_liability_account
                FROM kontenrahmen_konfiguration
                WHERE mandant_id = ?
                """,
                (mandant_id,),
            ).one()

            assert configuration == (
                "0846",
                "0855",
                "0755",
            )

            accounts = connection.exec_driver_sql(
                """
                SELECT
                    account_number,
                    name,
                    account_type,
                    is_active,
                    debit_position_code,
                    credit_position_code
                FROM konten
                WHERE mandant_id = ?
                  AND account_number IN (
                      '0755',
                      '0846',
                      '0855'
                  )
                ORDER BY account_number
                """,
                (mandant_id,),
            ).all()

            assert accounts == [
                (
                    "0755",
                    (
                        "Verbindlichkeiten gegenüber Gesellschaftern "
                        "für offene Ausschüttungen"
                    ),
                    "LIABILITY",
                    1,
                    None,
                    "HGB.266.PASSIVA.C.8",
                ),
                (
                    "0846",
                    "Individuelles bestehendes Konto",
                    "LIABILITY",
                    0,
                    "INDIVIDUAL.DEBIT",
                    "INDIVIDUAL.CREDIT",
                ),
                (
                    "0855",
                    "Andere Gewinnrücklagen",
                    "EQUITY",
                    1,
                    None,
                    "HGB.266.PASSIVA.A.III.4",
                ),
            ]
    finally:
        engine.dispose()

    assert (
        _current_revision(database_path)
        == "36fe523b87a4"
    )
    assert _foreign_key_check(database_path) == []


def test_profit_appropriation_postings_migration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Die Tabelle für bestätigte Ergebnisverwendungsbuchungen wird angelegt."""

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
        "36fe523b87a4",
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        assert (
            "gewinnverwendungsbuchungen"
            not in inspector.get_table_names()
        )
    finally:
        engine.dispose()

    command.upgrade(
        config,
        "eccb0d66e425",
    )

    engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(engine)

        assert (
            "gewinnverwendungsbuchungen"
            in inspector.get_table_names()
        )

        columns = {
            column["name"]
            for column in inspector.get_columns(
                "gewinnverwendungsbuchungen"
            )
        }

        assert columns == {
            "id",
            "posting_id",
            "quell_wirtschaftsjahr_id",
            "buchungszeile_id",
            "posting_date",
            "amount",
            "posting_type",
        }

        foreign_keys = inspector.get_foreign_keys(
            "gewinnverwendungsbuchungen"
        )

        assert any(
            foreign_key["constrained_columns"]
            == ["quell_wirtschaftsjahr_id"]
            and foreign_key["referred_table"]
            == "wirtschaftsjahre"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in foreign_keys
        )

        assert any(
            foreign_key["constrained_columns"]
            == ["buchungszeile_id"]
            and foreign_key["referred_table"]
            == "buchungszeilen"
            and foreign_key["referred_columns"]
            == ["id"]
            for foreign_key in foreign_keys
        )

        unique_constraints = (
            inspector.get_unique_constraints(
                "gewinnverwendungsbuchungen"
            )
        )

        assert any(
            constraint["column_names"]
            == ["posting_id"]
            for constraint in unique_constraints
        )

        assert any(
            constraint["column_names"]
            == ["buchungszeile_id"]
            for constraint in unique_constraints
        )

        assert not any(
            set(constraint["column_names"])
            == {
                "quell_wirtschaftsjahr_id",
                "posting_type",
            }
            for constraint in unique_constraints
        )
    finally:
        engine.dispose()

    assert (
        _current_revision(database_path)
        == "eccb0d66e425"
    )
    assert _foreign_key_check(database_path) == []
