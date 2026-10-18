"""Vollständiger, expliziter Löschpfad für das aktuelle Mandantenschema."""

from typing import Any
from uuid import UUID

from sqlalchemy import Connection, inspect, select, text

from simpleob.database.database import Base

# Bei neuen Modellen muss der Löschumfang bewusst geprüft und erweitert werden.
CLIENT_TABLE_NAMES = frozenset(
    {
        "mandanten",
        "konten",
        "konten_taxonomie_zuordnungen",
        "kontenrahmen_konfiguration",
        "kontenrollen",
        "wirtschaftsjahre",
        "buchungen",
        "buchungszeilen",
        "gesellschafter",
        "anlagegueter",
        "anlagebewegungen",
        "anlageabschreibungen",
        "steuerliche_afa_abweichungen",
        "gewinnverwendungs_jahresdaten",
        "gewinnverwendungsbuchungen",
        "eigenkapitaleinlagen",
    }
)

CapturedClient = dict[str, list[dict[str, Any]]]


def _id_batches(values):
    """Begrenzt SQL-Parameter auch für große Buchhaltungsbestände."""
    values = tuple(values)
    for start in range(0, len(values), 500):
        yield values[start : start + 500]


class ClientDeletionRepository:
    """Arbeitet ohne ORM-Kaskaden auf der extern verwalteten Transaktion."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        if set(Base.metadata.tables) != CLIENT_TABLE_NAMES:
            raise ValueError(
                "Der Löschpfad muss an die geänderten Datenbankmodelle angepasst werden."
            )
        self.tables = tuple(Base.metadata.sorted_tables)

    def lock_and_check_schema(self) -> None:
        schema = None
        if self.connection.dialect.name == "postgresql":
            self.connection.exec_driver_sql("SET LOCAL lock_timeout = '3000ms'")
            quote = self.connection.dialect.identifier_preparer.quote
            names = ", ".join(
                quote(t.name) for t in sorted(self.tables, key=lambda t: t.name)
            )
            # Blockiert auch SELECT FOR UPDATE, gewöhnliche Leser bleiben erlaubt.
            self.connection.exec_driver_sql(f"LOCK TABLE {names} IN EXCLUSIVE MODE")
            # Unqualifizierte Modelle folgen dem search_path, nicht zwingend
            # current_schema(). Jede gesperrte Tabelle muss im selben Schema liegen.
            schemas = {
                self.connection.execute(
                    text(
                        "SELECT n.nspname FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE c.oid = to_regclass(:name)"
                    ),
                    {"name": quote(table.name)},
                ).scalar_one()
                for table in self.tables
            }
            if len(schemas) != 1:
                raise ValueError("SimpleOB-Tabellen liegen in verschiedenen Schemas.")
            schema = schemas.pop()

        inspector = inspect(self.connection)
        expected = {table.name for table in self.tables}
        actual = set(inspector.get_table_names(schema=schema)) - {"alembic_version"}
        if actual != expected:
            raise ValueError(
                "Unbekanntes oder unvollständiges Datenbankschema; Löschung abgebrochen."
            )
        for table in self.tables:
            columns = {
                column["name"]
                for column in inspector.get_columns(table.name, schema=schema)
            }
            actual_fks = inspector.get_foreign_keys(
                table.name,
                schema=schema,
                **({"postgresql_ignore_search_path": True} if schema else {}),
            )
            fks = {
                (
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                )
                for fk in actual_fks
            }
            expected_fks = {
                ((fk.parent.name,), fk.column.table.name, (fk.column.name,))
                for fk in table.foreign_keys
            }
            if columns != set(table.c.keys()) or fks != expected_fks:
                raise ValueError(
                    f"Abweichendes Schema in {table.name}; Löschung abgebrochen."
                )
            if any(
                fk.get("referred_schema")
                not in (None, schema or inspector.default_schema_name)
                or fk.get("options", {}).get("ondelete", "NO ACTION")
                not in ("NO ACTION", "RESTRICT")
                for fk in actual_fks
            ):
                raise ValueError(f"Unerwartete Fremdschlüsselwirkung in {table.name}.")

        # Projektfremde Trigger könnten neben dem geprüften Bestand weitere
        # Mandanten verändern. Im aktuellen Schema gibt es keine solchen Trigger.
        if self.connection.dialect.name == "sqlite":
            triggers = self.connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' LIMIT 1"
            ).first()
        else:
            if self.connection.execute(
                text(
                    "SELECT fk.oid FROM pg_constraint fk "
                    "JOIN pg_class parent ON parent.oid = fk.confrelid "
                    "JOIN pg_namespace pn ON pn.oid = parent.relnamespace "
                    "JOIN pg_class child ON child.oid = fk.conrelid "
                    "JOIN pg_namespace cn ON cn.oid = child.relnamespace "
                    "WHERE fk.contype = 'f' AND pn.nspname = :schema "
                    "AND cn.nspname <> :schema LIMIT 1"
                ),
                {"schema": schema},
            ).first():
                raise ValueError(
                    "Ein fremdes Datenbankschema verweist auf Mandantendaten."
                )
            triggers = self.connection.execute(
                text(
                    "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE NOT t.tgisinternal AND n.nspname = :schema LIMIT 1"
                ),
                {"schema": schema},
            ).first()
        if triggers:
            raise ValueError("Unerwartete Datenbanktrigger; Löschung abgebrochen.")

    def capture(self, company_id: UUID) -> CapturedClient:
        """Erfasst alle direkten/indirekten Pfade und prüft ihre Übereinstimmung."""
        captured = {}
        ids = {}
        for table in self.tables:
            if table.name == "mandanten":
                statements = [
                    select(table).where(table.c.company_id == str(company_id))
                ]
            else:
                parents = [fk for fk in table.foreign_keys if fk.column.table != table]
                statements = (
                    select(table).where(fk.parent.in_(batch))
                    for fk in parents
                    for batch in _id_batches(ids[fk.column.table.name])
                )
            # Mehrfach verbundene Sätze können über mehrere Elternpfade erscheinen.
            by_id = {}
            for statement in statements:
                for row in self.connection.execute(statement).mappings():
                    by_id[row["id"]] = dict(row)
            rows = list(by_id.values())
            captured[table.name] = rows
            ids[table.name] = {row["id"] for row in rows}

        # Ein Datensatz darf nicht über einen Pfad dem Ziel und über einen
        # anderen Pfad einem fremden Mandanten (oder keinem Elternsatz) gehören.
        for table in self.tables:
            for row in captured[table.name]:
                for fk in table.foreign_keys:
                    value = row[fk.parent.name]
                    if value is not None and value not in ids[fk.column.table.name]:
                        raise ValueError(
                            f"Fremde oder beschädigte Beziehung in {table.name}."
                        )
            for fk in table.foreign_keys:
                for batch in _id_batches(ids[fk.column.table.name]):
                    referenced = self.connection.execute(
                        select(table.c.id).where(fk.parent.in_(batch))
                    ).scalars()
                    if any(row_id not in ids[table.name] for row_id in referenced):
                        raise ValueError(
                            f"Eine fremde Beziehung verweist auf den Mandanten: {table.name}."
                        )

        # Buchungsstornos sind fachliche UUID-Referenzen ohne Datenbank-FK.
        bookings = Base.metadata.tables["buchungen"]
        booking_ids = {row["booking_id"] for row in captured["buchungen"]}
        for batch in _id_batches(booking_ids):
            referenced = self.connection.execute(
                select(bookings.c.id).where(
                    bookings.c.reversal_of_booking_id.in_(batch)
                )
            ).scalars()
            if any(row_id not in ids["buchungen"] for row_id in referenced):
                raise ValueError(
                    "Eine fremde Stornobuchung verweist auf den Mandanten."
                )
        return captured

    @staticmethod
    def canonical(captured: CapturedClient) -> dict[str, list[tuple]]:
        """Ersetzt ausschließlich technische IDs durch fachliche Referenzen."""
        rows = {
            name: {row["id"]: row for row in values}
            for name, values in captured.items()
        }

        def identity(name, row_id):
            row = rows[name][row_id]
            natural = {
                "mandanten": "company_id",
                "buchungen": "booking_id",
                "anlagegueter": "fixed_asset_id",
                "anlagebewegungen": "movement_id",
                "anlageabschreibungen": "depreciation_id",
            }
            if name in natural:
                return row[natural[name]]
            if name == "wirtschaftsjahre":
                return (
                    identity("mandanten", row["mandant_id"]),
                    row["start_date"],
                    row["end_date"],
                )
            if name == "buchungszeilen":
                return (identity("buchungen", row["buchung_id"]), row["position"])
            raise ValueError(f"Unbekanntes Referenzziel: {name}")

        result = {}
        for table in Base.metadata.sorted_tables:
            converted = []
            fk_columns = {
                fk.parent.name: fk.column.table.name for fk in table.foreign_keys
            }
            for row in captured[table.name]:
                converted.append(
                    tuple(
                        (
                            name,
                            identity(fk_columns[name], value)
                            if name in fk_columns and value is not None
                            else value,
                        )
                        for name, value in sorted(row.items())
                        if name != "id"
                    )
                )
            result[table.name] = sorted(converted, key=repr)
        return result

    def delete_captured(self, captured: CapturedClient) -> None:
        # Selbstreferenzen erst NACH der Sicherung entfernen; fremde eingehende
        # Referenzen wurden zuvor ausgeschlossen. Alle Änderungen sind rollbackfähig.
        for table in self.tables:
            ids = [row["id"] for row in captured[table.name]]
            for fk in table.foreign_keys:
                if fk.column.table == table:
                    for batch in _id_batches(ids):
                        self.connection.execute(
                            table.update()
                            .where(table.c.id.in_(batch))
                            .values({fk.parent.name: None})
                        )
        for table in reversed(self.tables):
            ids = [row["id"] for row in captured[table.name]]
            for batch in _id_batches(ids):
                result = self.connection.execute(
                    table.delete().where(table.c.id.in_(batch))
                )
                if result.rowcount != len(batch):
                    raise ValueError(f"Unerwarteter Löschumfang in {table.name}.")

    def check_deleted(self, captured: CapturedClient) -> None:
        for table in self.tables:
            checks = [(table.c.id, table.name)]
            for fk in table.foreign_keys:
                checks.append((fk.parent, fk.column.table.name))
            for column, parent in checks:
                for batch in _id_batches(row["id"] for row in captured[parent]):
                    if self.connection.execute(
                        select(table.c.id).where(column.in_(batch)).limit(1)
                    ).first():
                        raise ValueError(
                            f"Mandantendaten sind in {table.name} zurückgeblieben."
                        )
