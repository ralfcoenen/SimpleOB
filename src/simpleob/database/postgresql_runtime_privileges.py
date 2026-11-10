"""Minimal runtime grants shared by PostgreSQL setup and maintenance paths."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.engine import Connection


def grant_application_table_privileges(
    connection: Connection,
    *,
    operating_role: str,
    table_names: Iterable[str],
) -> None:
    """Grant normal DML only on application tables, never on Alembic state."""

    quote = connection.dialect.identifier_preparer.quote_identifier
    role = quote(operating_role)
    for table_name in sorted(table_names):
        if table_name == "alembic_version":
            continue
        connection.exec_driver_sql(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
            f"public.{quote(table_name)} TO {role}"
        )


def enforce_read_only_alembic_version(
    connection: Connection,
    *,
    operating_role: str,
) -> None:
    """Keep Alembic state readable but not writable by the runtime role.

    Table-specific ACLs are needed because the migration owner's default
    privileges intentionally grant DML on newly created application tables.
    Effective rights are checked separately so PUBLIC or inherited grants
    cannot silently bypass this restriction.
    """

    quote = connection.dialect.identifier_preparer.quote_identifier
    role = quote(operating_role)
    version_table = f"public.{quote('alembic_version')}"
    connection.exec_driver_sql(f"GRANT SELECT ON TABLE {version_table} TO {role}")
    connection.exec_driver_sql(
        f"REVOKE INSERT, UPDATE, DELETE ON TABLE {version_table} FROM {role}"
    )
