"""Ausdrücklich bestätigtes PostgreSQL-Upgrade vor dem Anwendungsstart."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)
from sqlalchemy.engine import make_url

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.migration_service import (
    PostgreSQLSchemaInspection,
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_administration_service import (
    PostgreSQLAdministrationService,
)
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLExistingInstallationAssessment,
    PostgreSQLExistingInstallationInspector,
)
from simpleob.database.postgresql_migration_safety import PostgreSQLMigrationApproval
from simpleob.ui_qt.postgresql_password_dialog import PostgreSQLPasswordDialog


def prepare_postgresql_candidate(
    config: ApplicationConfig,
    operating_credentials: PostgreSQLCredentials,
    *,
    parent=None,
) -> str:
    """Prüft eine PostgreSQL-Auswahl und migriert veraltete Datenbanken sofort.

    Die Konfiguration bleibt unverändert. Eine Rückgabe "ready" erfolgt erst,
    wenn die Betriebsrolle nach der Prüfung oder dem Upgrade ein aktuelles,
    konsistentes Schema mit den erforderlichen Rechten erreicht.
    """
    assessment = PostgreSQLExistingInstallationInspector(
        application_config=config,
        credentials=operating_credentials,
    ).inspect()

    if assessment.schema_status == PostgreSQLSchemaStatus.CURRENT:
        _require_operational_assessment(assessment)
        return "ready"

    if assessment.schema_status == PostgreSQLSchemaStatus.EMPTY:
        raise RuntimeError(
            "Die ausgewählte PostgreSQL-Datenbank ist leer. "
            "Eine PostgreSQL-Ersteinrichtung ist erforderlich."
        )

    if assessment.schema_status == PostgreSQLSchemaStatus.UNKNOWN:
        raise RuntimeError(
            "Die ausgewählte PostgreSQL-Datenbank hat einen unbekannten "
            "oder inkonsistenten Alembic-Schemazustand. Der Betrieb bleibt gesperrt."
        )

    inspection = PostgreSQLSchemaInspection(
        status=assessment.schema_status,
        current_revision=assessment.current_revision,
        head_revision=assessment.head_revision,
    )
    if parent is None:
        action = offer_postgresql_upgrade(
            config,
            operating_credentials,
            inspection,
        )
    else:
        action = offer_postgresql_upgrade(
            config,
            operating_credentials,
            inspection,
            parent=parent,
        )
    if action != "ready":
        return action

    verified = PostgreSQLExistingInstallationInspector(
        application_config=config,
        credentials=operating_credentials,
    ).inspect()
    _require_operational_assessment(verified)
    return "upgraded"


def _require_operational_assessment(
    assessment: PostgreSQLExistingInstallationAssessment,
) -> None:
    if assessment.schema_status != PostgreSQLSchemaStatus.CURRENT:
        raise RuntimeError(
            "Die PostgreSQL-Datenbank ist nach der Vorbereitung nicht aktuell. "
            "Der Betrieb bleibt gesperrt."
        )
    if assessment.blockers:
        raise RuntimeError(
            "Die PostgreSQL-Datenbank ist nicht betriebsbereit. "
            "Der Betrieb bleibt gesperrt.\n"
            + "\n".join(assessment.blockers)
        )


def offer_postgresql_upgrade(
    config: ApplicationConfig,
    operating_credentials: PostgreSQLCredentials,
    inspection: PostgreSQLSchemaInspection,
    *,
    parent=None,
) -> str:
    """Liefert ready, change oder cancel; speichert keine Zugangsdaten."""
    url = make_url(config.database_url)
    database = url.database or ""
    box = QMessageBox(parent)
    if parent is not None:
        box.setWindowModality(Qt.WindowModality.WindowModal)
    box.setWindowTitle("SimpleOB – PostgreSQL-Schema")
    box.setText(
        f"Datenbank: {database}\n"
        f"Aktuelle Alembic-Revision: {inspection.current_revision or 'nicht vorhanden'}\n"
        f"Erwartete Alembic-Revision: {inspection.head_revision}\n\n"
        "Der Buchhaltungsbetrieb bleibt bis zur erfolgreichen Schemaprüfung gesperrt."
    )
    upgrade = None
    if inspection.status == PostgreSQLSchemaStatus.OUTDATED:
        upgrade = box.addButton(
            "Administratives Upgrade …", QMessageBox.ButtonRole.ActionRole
        )
    else:
        box.setInformativeText(
            "Der Schemazustand ist unbekannt oder nicht für ein Upgrade geeignet. "
            "Ein Upgrade wird nicht angeboten."
        )
    change = box.addButton(
        "Datenbankverbindung ändern …", QMessageBox.ButtonRole.ActionRole
    )
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    if box.clickedButton() is change:
        return "change"
    if upgrade is None or box.clickedButton() is not upgrade:
        return "cancel"

    confirmed, accepted = QInputDialog.getText(
        parent,
        "Schema-Upgrade bestätigen",
        f"Zieldatenbank: {database}\n"
        f"Revision {inspection.current_revision} → {inspection.head_revision}\n\n"
        "Das Upgrade verändert das Datenbankschema. Alle anderen SimpleOB-"
        "Verbindungen müssen beendet sein. Vorher werden eine vollständige "
        "Sicherung und eine tatsächliche Wiederherstellungsprobe durchgeführt. "
        "Eine automatische Wiederherstellung erfolgt nicht.\n\n"
        "Geben Sie zur ausdrücklichen Zustimmung den exakten Datenbanknamen ein:",
    )
    if not accepted:
        return "cancel"
    if confirmed != database:
        QMessageBox.warning(
            parent, "Upgrade nicht bestätigt", "Der Datenbankname stimmt nicht überein."
        )
        return "change"

    def request_role(label):
        username, accepted = QInputDialog.getText(parent, "PostgreSQL-Upgrade", label)
        if not accepted or not username.strip():
            return None
        dialog = PostgreSQLPasswordDialog(
            username=username.strip(),
            host=url.host or "",
            database=database,
            parent=parent,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        credentials = PostgreSQLCredentials(dialog.password)
        dialog._password_edit.clear()
        return username.strip(), credentials

    migration = request_role("Migrationsrolle (Eigentümerin der SimpleOB-Objekte):")
    if migration is None:
        return "cancel"
    administration = request_role(
        "Administrationsrolle (Wiederherstellungsprobe und Wartung):"
    )
    if administration is None:
        return "cancel"
    filename, _ = QFileDialog.getSaveFileName(
        parent,
        "Sicherung vor dem Schema-Upgrade",
        str(config.data_dir / "simpleob-vor-upgrade.dump"),
        "PostgreSQL-Sicherung (*.dump)",
    )
    if not filename:
        return "cancel"

    try:
        PostgreSQLAdministrationService(
            application_config=config,
            operating_username=url.username,
            operating_credentials=operating_credentials,
            migration_username=migration[0],
            migration_credentials=migration[1],
            admin_username=administration[0],
            admin_credentials=administration[1],
        ).execute_migration(
            approval=PostgreSQLMigrationApproval(
                migration_confirmed=True,
                maintenance_confirmed=True,
                confirmed_database_name=confirmed,
            ),
            backup_path=Path(filename),
        )
    except Exception as exc:
        # Nur eigene fachliche Meldungen übernehmen; DBAPI-/Werkzeugfehler
        # können Verbindungsdetails enthalten. Zugangsdaten immer entfernen.
        detail = ""
        if type(exc) in (RuntimeError, ValueError, PermissionError):
            detail = str(exc)
            for credentials in (operating_credentials, migration[1], administration[1]):
                if credentials.password:
                    detail = detail.replace(credentials.password, "[entfernt]")
            detail = detail + "\n\n"
        QMessageBox.warning(
            parent,
            "PostgreSQL-Upgrade fehlgeschlagen",
            detail
            + "Das Upgrade wurde nicht erfolgreich abgeschlossen. Der Betrieb bleibt "
            "gesperrt. Bitte Rollenrechte, Sicherung und Datenbankzustand einschließlich "
            "der Wartungssperre administrativ prüfen. Es erfolgt weder eine automatische "
            "Wiederholung noch eine automatische Wiederherstellung.",
        )
        return "change"
    finally:
        migration = None
        administration = None
    return "ready"
