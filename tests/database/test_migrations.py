"""Tests für die Datenbankmigrationen."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError

BASELINE_REVISION = "7392d6cc6892"
HEAD_REVISION = "b7d41a8f2c60"


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


def test_paid_invoice_cancellation_schema_backfills_and_checks_origins(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Das 4D-3a-Schema erhält Altstornos und erzwingt Guthabenherkunft."""

    database_path = tmp_path / "paid-cancellation-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("OPENBILANZ_DATABASE_URL", database_url)
    config = _alembic_config(database_path)
    command.upgrade(config, "d4a2f19c7b60")

    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO mandanten (id, company_id, name) "
                "VALUES (1, 'company-1', 'Migrationstest')"
            ))
            connection.execute(text(
                "INSERT INTO geschaeftspartner "
                "(id, partner_id, mandant_id, name, is_customer, is_supplier, is_active) "
                "VALUES (1, 'partner-1', 1, 'Partner', 1, 1, 1)"
            ))
            connection.execute(text(
                "INSERT INTO wirtschaftsjahre "
                "(id, mandant_id, start_date, end_date, status) "
                "VALUES (1, 1, '2026-01-01', '2026-12-31', 'OPEN')"
            ))
            for booking_id, booking_date, kind, reversal_of in (
                ('source-1', '2026-01-10', 'REGULAR', None),
                ('reversal-1', '2026-02-10', 'REVERSAL', 'source-1'),
                ('source-2', '2026-01-11', 'REGULAR', None),
                ('reversal-2', '2026-02-11', 'REVERSAL', 'source-2'),
                ('credit-booking', '2026-01-12', 'REGULAR', None),
                ('refund-booking-1', '2026-03-01', 'REGULAR', None),
                ('refund-booking-2', '2026-03-02', 'REGULAR', None),
                ('refund-booking-3', '2026-03-03', 'REGULAR', None),
            ):
                connection.execute(text(
                    "INSERT INTO buchungen "
                    "(booking_id, wirtschaftsjahr_id, booking_date, booking_type, "
                    "reversal_of_booking_id) "
                    "VALUES (:booking_id, 1, :booking_date, :kind, :reversal_of)"
                ), {
                    "booking_id": booking_id,
                    "booking_date": booking_date,
                    "kind": kind,
                    "reversal_of": reversal_of,
                })
            for invoice_id, number, booking_id in (
                ('invoice-1', 'AR-OLD', 'source-1'),
                ('invoice-2', 'AR-ZERO', 'source-2'),
            ):
                connection.execute(text(
                    "INSERT INTO ausgangsrechnungen "
                    "(invoice_id, mandant_id, partner_id, invoice_number, invoice_date, "
                    "due_date, gross_amount, booking_id) "
                    "VALUES (:invoice_id, 1, 'partner-1', :number, '2026-01-10', "
                    "'2026-01-31', 119.00, :booking_id)"
                ), {
                    "invoice_id": invoice_id,
                    "number": number,
                    "booking_id": booking_id,
                })
            connection.execute(text(
                "INSERT INTO forderungs_ops (open_item_id, invoice_id, amount) "
                "VALUES ('op-1', 'invoice-1', 119.00), ('op-2', 'invoice-2', 119.00)"
            ))
            connection.execute(text(
                "INSERT INTO rechnungs_op_stornos "
                "(storno_id, mandant_id, partner_id, receivable_invoice_id, "
                "receivable_open_item_id, booking_id, amount, recorded_at, reason) "
                "VALUES ('storno-old', 1, 'partner-1', 'invoice-1', 'op-1', "
                "'reversal-1', 119.00, '2026-02-10 12:00:00', 'Altstorno')"
            ))
            connection.execute(text(
                "INSERT INTO gutschriften "
                "(credit_note_id, mandant_id, partner_id, credit_note_kind, note_number, "
                "note_date, booking_id) "
                "VALUES ('credit-1', 1, 'partner-1', 'CUSTOMER', 'GS-1', "
                "'2026-01-12', 'credit-booking')"
            ))
            connection.execute(text(
                "INSERT INTO guthaben_ops (open_item_id, credit_note_id, amount) "
                "VALUES ('credit-op-1', 'credit-1', 20.00)"
            ))
    finally:
        engine.dispose()

    command.upgrade(config, HEAD_REVISION)
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys_after_upgrade(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with engine.begin() as connection:
            legacy_amounts = connection.execute(text(
                "SELECT amount, closed_open_amount FROM rechnungs_op_stornos "
                "WHERE storno_id='storno-old'"
            )).one()
            assert tuple(legacy_amounts) == (119, 119)

            # Fully bezahlte Rechnungen dürfen den OP mit null schließen.
            connection.execute(text(
                "INSERT INTO rechnungs_op_stornos "
                "(storno_id, mandant_id, partner_id, receivable_invoice_id, "
                "receivable_open_item_id, booking_id, amount, closed_open_amount, "
                "recorded_at, reason) VALUES ('storno-zero', 1, 'partner-1', "
                "'invoice-2', 'op-2', 'reversal-2', 119.00, 0.00, "
                "'2026-02-11 12:00:00', 'Vollständig bezahlt')"
            ))

            # Die bestehende Gutschriftquelle bleibt erhalten; Storno ist zweite Quelle.
            existing_credit = connection.execute(text(
                "SELECT credit_note_id, invoice_cancellation_id "
                "FROM guthaben_ops WHERE open_item_id='credit-op-1'"
            )).one()
            assert tuple(existing_credit) == ('credit-1', None)
            connection.execute(text(
                "INSERT INTO guthaben_ops "
                "(open_item_id, credit_note_id, invoice_cancellation_id, amount) "
                "VALUES ('storno-credit-op', NULL, 'storno-old', 40.00)"
            ))

            assert connection.execute(text(
                "SELECT count(*) FROM guthaben_ops "
                "WHERE invoice_cancellation_id='storno-old'"
            )).scalar_one() == 1

            connection.execute(text(
                "INSERT INTO guthaben_op_rueckerstattungen "
                "(refund_id, mandant_id, partner_id, open_item_id, direction, "
                "amount, refund_date, booking_id, recorded_at) VALUES "
                "('refund-credit-note', 1, 'partner-1', 'credit-op-1', "
                "'CUSTOMER', 5.00, '2026-03-01', 'refund-booking-1', "
                "'2026-03-01 10:00:00+00:00'), "
                "('refund-cancellation', 1, 'partner-1', 'storno-credit-op', "
                "'CUSTOMER', 10.00, '2026-03-02', 'refund-booking-2', "
                "'2026-03-02 10:00:00+00:00')"
            ))
            assert connection.execute(text(
                "SELECT count(*) FROM guthaben_op_rueckerstattungen "
                "WHERE open_item_id='credit-op-1'"
            )).scalar_one() == 1

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_ops "
                    "(open_item_id, credit_note_id, invoice_cancellation_id, amount) "
                    "VALUES ('both-sources', 'credit-1', 'storno-zero', 10.00)"
                ))
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_ops "
                    "(open_item_id, credit_note_id, invoice_cancellation_id, amount) "
                    "VALUES ('no-source', NULL, NULL, 10.00)"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungen "
                    "(refund_id, mandant_id, partner_id, open_item_id, direction, "
                    "amount, refund_date, booking_id, recorded_at) VALUES "
                    "('refund-invalid-direction', 1, 'partner-1', 'credit-op-1', "
                    "'INVALID', 1.00, '2026-03-03', 'refund-booking-3', "
                    "'2026-03-03 10:00:00+00:00')"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungen "
                    "(refund_id, mandant_id, partner_id, open_item_id, direction, "
                    "amount, refund_date, booking_id, recorded_at) VALUES "
                    "('refund-invalid-amount', 1, 'partner-1', 'credit-op-1', "
                    "'CUSTOMER', 0.00, '2026-03-03', 'refund-booking-3', "
                    "'2026-03-03 10:00:00+00:00')"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungen "
                    "(refund_id, mandant_id, partner_id, open_item_id, direction, "
                    "amount, refund_date, booking_id, recorded_at) VALUES "
                    "('refund-invalid-partner', 1, 'foreign-partner', 'credit-op-1', "
                    "'CUSTOMER', 1.00, '2026-03-03', 'refund-booking-3', "
                    "'2026-03-03 10:00:00+00:00')"
                ))

        inspector = inspect(engine)
        storno_columns = {
            column["name"]
            for column in inspector.get_columns("rechnungs_op_stornos")
        }
        assert {"closed_open_amount", "credit_booking_id"} <= storno_columns
        assert any(
            fk["constrained_columns"] == ["invoice_cancellation_id"]
            and fk["referred_table"] == "rechnungs_op_stornos"
            for fk in inspector.get_foreign_keys("guthaben_ops")
        )
        refund_columns = {
            column["name"]
            for column in inspector.get_columns(
                "guthaben_op_rueckerstattungen"
            )
        }
        assert refund_columns == {
            "id",
            "refund_id",
            "mandant_id",
            "partner_id",
            "open_item_id",
            "direction",
            "amount",
            "refund_date",
            "booking_id",
            "recorded_at",
        }
        refund_foreign_keys = inspector.get_foreign_keys(
            "guthaben_op_rueckerstattungen"
        )
        assert any(
            fk["constrained_columns"] == ["mandant_id", "partner_id"]
            and fk["referred_table"] == "geschaeftspartner"
            and fk["referred_columns"] == ["mandant_id", "partner_id"]
            for fk in refund_foreign_keys
        )
        assert any(
            fk["constrained_columns"] == ["open_item_id"]
            and fk["referred_table"] == "guthaben_ops"
            for fk in refund_foreign_keys
        )
        assert any(
            fk["constrained_columns"] == ["booking_id"]
            and fk["referred_table"] == "buchungen"
            for fk in refund_foreign_keys
        )
        refund_uniques = inspector.get_unique_constraints(
            "guthaben_op_rueckerstattungen"
        )
        assert {tuple(item["column_names"]) for item in refund_uniques} == {
            ("refund_id",),
            ("booking_id",),
        }
        refund_checks = inspector.get_check_constraints(
            "guthaben_op_rueckerstattungen"
        )
        assert {item["name"] for item in refund_checks} == {
            "ck_guthaben_op_refund_richtung",
            "ck_guthaben_op_refund_betrag_positiv",
        }
        assert {
            item["name"]
            for item in inspector.get_indexes(
                "guthaben_op_rueckerstattungen"
            )
        } >= {"ix_guthaben_op_refund_open_item"}
        assert _current_revision(database_path) == HEAD_REVISION
        assert _foreign_key_check(database_path) == []
    finally:
        engine.dispose()


def test_credit_refund_reversal_migration_preserves_refunds_and_constraints(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Die Rücknahmemigration erhält Rückerstattungen und sichert Referenzen."""

    database_path = tmp_path / "credit-refund-reversal.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("OPENBILANZ_DATABASE_URL", database_url)
    config = _alembic_config(database_path)
    command.upgrade(config, "f2a91c7d5e30")

    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO mandanten (id, company_id, name) "
                "VALUES (1, 'company-1', 'Migrationstest')"
            ))
            connection.execute(text(
                "INSERT INTO geschaeftspartner "
                "(id, partner_id, mandant_id, name, is_customer, is_supplier, is_active) "
                "VALUES (1, 'partner-1', 1, 'Partner', 1, 0, 1)"
            ))
            connection.execute(text(
                "INSERT INTO wirtschaftsjahre "
                "(id, mandant_id, start_date, end_date, status) "
                "VALUES (1, 1, '2026-01-01', '2026-12-31', 'OPEN')"
            ))
            connection.execute(text(
                "INSERT INTO buchungen "
                "(booking_id, wirtschaftsjahr_id, booking_date, booking_type) "
                "VALUES ('refund-booking', 1, '2026-03-01', 'REGULAR'), "
                "('refund-booking-2', 1, '2026-03-01', 'REGULAR'), "
                "('refund-reversal', 1, '2026-03-02', 'REVERSAL'), "
                "('refund-reversal-2', 1, '2026-03-03', 'REVERSAL')"
            ))
            connection.execute(text(
                "INSERT INTO gutschriften "
                "(credit_note_id, mandant_id, partner_id, credit_note_kind, "
                "note_number, note_date, booking_id) "
                "VALUES ('credit-1', 1, 'partner-1', 'CUSTOMER', 'GS-1', "
                "'2026-02-28', 'refund-booking')"
            ))
            connection.execute(text(
                "INSERT INTO guthaben_ops (open_item_id, credit_note_id, amount) "
                "VALUES ('credit-op-1', 'credit-1', 75.00)"
            ))
            connection.execute(text(
                "INSERT INTO guthaben_op_rueckerstattungen "
                "(refund_id, mandant_id, partner_id, open_item_id, direction, "
                "amount, refund_date, booking_id, recorded_at) VALUES "
                "('refund-1', 1, 'partner-1', 'credit-op-1', 'CUSTOMER', "
                "25.00, '2026-03-01', 'refund-booking', '2026-03-01 10:00:00+00:00'), "
                "('refund-2', 1, 'partner-1', 'credit-op-1', 'CUSTOMER', "
                "5.00, '2026-03-01', 'refund-booking-2', '2026-03-01 11:00:00+00:00')"
            ))
            before = connection.execute(text(
                "SELECT refund_id, mandant_id, partner_id, open_item_id, direction, "
                "amount, refund_date, booking_id, recorded_at "
                "FROM guthaben_op_rueckerstattungen WHERE refund_id='refund-1'"
            )).one()
    finally:
        engine.dispose()

    command.upgrade(config, HEAD_REVISION)
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys_after_upgrade(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with engine.begin() as connection:
            after = connection.execute(text(
                "SELECT refund_id, mandant_id, partner_id, open_item_id, direction, "
                "amount, refund_date, booking_id, recorded_at "
                "FROM guthaben_op_rueckerstattungen WHERE refund_id='refund-1'"
            )).one()
            assert tuple(after) == tuple(before)

            connection.execute(text(
                "INSERT INTO guthaben_op_rueckerstattungsruecknahmen "
                "(reversal_id, refund_id, reversal_booking_id, recorded_at, reason) "
                "VALUES ('undo-1', 'refund-1', 'refund-reversal', "
                "'2026-03-02 12:00:00+00:00', 'Irrtümlich erfasst')"
            ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungsruecknahmen "
                    "(reversal_id, refund_id, reversal_booking_id, recorded_at, reason) "
                    "VALUES ('undo-duplicate', 'refund-1', 'refund-reversal-2', "
                    "'2026-03-03 12:00:00+00:00', 'Doppelversuch')"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungsruecknahmen "
                    "(reversal_id, refund_id, reversal_booking_id, recorded_at, reason) "
                    "VALUES ('undo-empty-reason', 'refund-2', 'refund-reversal-2', "
                    "'2026-03-03 12:00:00+00:00', '   ')"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungsruecknahmen "
                    "(reversal_id, refund_id, reversal_booking_id, recorded_at, reason) "
                    "VALUES ('undo-missing-refund', 'missing-refund', 'refund-reversal-2', "
                    "'2026-03-03 12:00:00+00:00', 'Test')"
                ))

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO guthaben_op_rueckerstattungsruecknahmen "
                    "(reversal_id, refund_id, reversal_booking_id, recorded_at, reason) "
                    "VALUES ('undo-missing-booking', 'refund-2', 'missing-booking', "
                    "'2026-03-03 12:00:00+00:00', 'Test')"
                ))

        inspector = inspect(engine)
        table = "guthaben_op_rueckerstattungsruecknahmen"
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        assert set(columns) == {
            "id", "reversal_id", "refund_id", "reversal_booking_id",
            "recorded_at", "reason",
        }
        assert all(
            not columns[name]["nullable"]
            for name in (
                "reversal_id", "refund_id", "reversal_booking_id",
                "recorded_at", "reason",
            )
        )
        foreign_keys = inspector.get_foreign_keys(table)
        assert {
            (tuple(fk["constrained_columns"]), fk["referred_table"])
            for fk in foreign_keys
        } == {
            (("refund_id",), "guthaben_op_rueckerstattungen"),
            (("reversal_booking_id",), "buchungen"),
        }
        unique_columns = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints(table)
        }
        assert unique_columns == {
            ("reversal_id",), ("refund_id",), ("reversal_booking_id",),
        }
        assert {
            item["name"] for item in inspector.get_check_constraints(table)
        } == {"ck_guthaben_op_ruecknahme_grund_nichtleer"}
        assert _current_revision(database_path) == HEAD_REVISION
        assert _foreign_key_check(database_path) == []
    finally:
        engine.dispose()


def test_paid_invoice_cancellation_migration_downgrade_and_reupgrade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Die neue Migration lässt sich isoliert zurücknehmen und erneut anwenden."""

    database_path = tmp_path / "paid-cancellation-roundtrip.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("OPENBILANZ_DATABASE_URL", database_url)
    config = _alembic_config(database_path)

    command.upgrade(config, "d4a2f19c7b60")
    command.upgrade(config, HEAD_REVISION)
    command.downgrade(config, "d4a2f19c7b60")
    assert _current_revision(database_path) == "d4a2f19c7b60"

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        storno_columns = {
            column["name"]
            for column in inspector.get_columns("rechnungs_op_stornos")
        }
        credit_columns = {
            column["name"]
            for column in inspector.get_columns("guthaben_ops")
        }
        assert "closed_open_amount" not in storno_columns
        assert "credit_booking_id" not in storno_columns
        assert "invoice_cancellation_id" not in credit_columns
    finally:
        engine.dispose()

    command.upgrade(config, HEAD_REVISION)
    assert _current_revision(database_path) == HEAD_REVISION
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
