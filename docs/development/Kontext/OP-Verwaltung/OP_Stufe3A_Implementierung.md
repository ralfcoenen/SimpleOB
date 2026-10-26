# OP-Verwaltung – Implementierungsstufe 3A

Stand: 26.10.2026
Ausgangspunkt: Commit `8e059b0`
Status: Implementierung uncommitted; kein Commit erstellt.

## Umfang und Ergebnis

Die OP-Verwaltung unterstützt jetzt tatsächliche Zahlungen auf bestehende Ausgangs- und Eingangsrechnungen. Eine Zahlung wird genau einem Rechnungs-OP zugeordnet; Voll- und Teilzahlungen sind möglich. Eine Überzahlung wird abgewiesen. Sammelzahlungen, Anzahlungen, Guthabenverrechnungen, Rückzahlungen, Storno-/Korrekturworkflows und §-19-Automatik wurden nicht ergänzt.

Der Buchungsbereich enthält einen Dialog „Zahlung auf Rechnung erfassen“. Er bietet offene Rechnungs-OPs und die für den Mandanten konfigurierten Bank-/Kassenkonten an. Das tatsächliche Zahlungsdatum wird getrennt vom Buchungsdatum gespeichert. Der Erfassungszeitpunkt wird beim Erzeugen der unveränderlichen Domänenzahlung als UTC-Zeitstempel festgehalten.

## Fachlicher und technischer Ablauf

- Kundenzahlung: Bank/Kasse im Soll, Forderungskonto im Haben.
- Lieferantenzahlung: Verbindlichkeitskonto im Soll, Bank/Kasse im Haben.
- Je Zahlung wird nur ein `Booking` über `BookingRepository.add(..., commit=False)` geschrieben. Die Nebenbuchzahlung und genau ein Zahlungszuordnungsereignis werden mit derselben Session ergänzt; der Service ruft anschließend einmal `commit()` auf. Bei jedem Fehler rollt er die gemeinsame Session zurück.
- Die Zahlungsbuchung referenziert den OP über `booking_id`; `Zahlung.booking_id` ist eindeutig. Damit wird keine zweite Bank- oder Kassenbewegung erzeugt.
- Der offene Betrag ist der unveränderliche OP-Ursprungsbetrag abzüglich der Summe seiner Zahlungszuordnungsereignisse. Ein gespeicherter Restsaldo wird nicht eingeführt.
- Der OP wird vor der Buchung gesperrt, soweit das Datenbanksystem `SELECT … FOR UPDATE` unterstützt. Die Prüfung wird beim Persistieren erneut ausgeführt. SQLite bietet keine entsprechende Zeilensperre.
- Beträge müssen positiv sein und dürfen den aktuell offenen Rest nicht überschreiten. Partner, passende Kunden-/Lieferantenrolle, Mandant, offener OP, Forderungs-/Verbindlichkeitskonto, Bank-/Kassenkonto, Hauptbuchreferenz und Geschäftsjahr werden validiert. Das Buchungsdatum muss im ausgewählten offenen Geschäftsjahr liegen; das tatsächliche Zahlungsdatum bleibt separat.
- Datenbank-Constraints sichern positive Beträge, gültige Richtungen, eine Zuordnung pro Zahlung, eindeutige IDs und genau einen zur Zahlungsrichtung passenden OP-Fremdschlüssel. Domänenobjekte für Zahlung und Ereignis sind eingefroren; es gibt keinen Änderungsworkflow.

## Geänderte OP-Dateien

- `src/simpleob/domain/open_item_payment.py` – Zahlungsrichtungen, Zahlung, OP-Zahlungsereignis und Rechnungssummary.
- `src/simpleob/database/models.py` – Tabellen `zahlungen` und `rechnungs_op_zahlungsereignisse`.
- `src/simpleob/database/open_item_payment_repository.py` – Persistenz, Mandanten-/Partner-/Geschäftsjahresprüfung und Restberechnung.
- `src/simpleob/database/chart_of_accounts_repository.py` – Validierung eines konfigurierten, aktiven, mandanteneigenen Bank-/Kassenkontos; Kontotyp Aktiv.
- `src/simpleob/services/open_item_payment_service.py` – Kontierung, Überzahlungsprüfung und atomarer Buchungsablauf.
- `src/simpleob/ui_qt/open_item_payment_dialog.py` – Eingabedialog.
- `src/simpleob/ui_qt/main_window.py`, `src/simpleob/qt_main.py` – Dialogintegration in den Buchungsbereich und Serviceverdrahtung.
- `migrations/versions/a3e4c7f61b20_add_invoice_payment_events.py` – Alembic-Schemaänderung für beide Datenbanken.
- `tests/database/test_migration_service.py` – erwartete Alembic-Head-Revision.
- `tests/integration/test_open_item_payment.py` – gezielte Zahlungs- und Regressionstests.

Vorhandene unabhängige Änderungen im Arbeitsbaum (PostgreSQL-Benutzerverwaltung, Benutzerhandbuch und ältere Kontextdokumente) wurden nicht bearbeitet oder gestaged.

## Ausgeführte Prüfungen

- `tests/integration/test_open_item_payment.py`
- `tests/integration/test_receivable_invoice_posting.py`
- `tests/integration/test_payable_invoice_posting.py`
- `tests/integration/test_credit_note_posting.py`
- `tests/integration/test_persistent_booking_workflow.py`
- `tests/database/test_booking_repository.py`
- `tests/services/test_vat_booking_service.py`

Zusammen mit `tests/database/test_migration_service.py -k 'not postgresql'`: **58 Tests bestanden, 15 PostgreSQL-Tests ausgelassen**.
- Ruff für alle geänderten OP-Quell- und Testdateien: **bestanden**.
- `git diff --check`: **bestanden**.
- PostgreSQL-Verbindung: `SIMPLEOB_POSTGRES_TEST_URL` ist gesetzt, der lokale Server lehnt die Verbindung jedoch mit `fe_sendauth: no password supplied` ab. Daher konnte die neue Migration in dieser Umgebung nicht gegen PostgreSQL ausgeführt werden. SQLite-Migration und Constraints sind durch Tests geprüft.

Die vorhandenen Ausgangs-/Eingangsrechnungen, Gutschriften, VAT-Buchungslogik und gewöhnliche Buchungsabläufe wurden durch die oben genannten Regressionstests mitgeprüft. E-Bilanz/ERiC und Mandanten-Datenverwaltung wurden nicht verändert.

## Verbleibende Einschränkungen

- PostgreSQL-Migration und -Transaktion konnten wegen fehlender Testdatenbank-Anmeldedaten nicht praktisch verifiziert werden.
- SQLite sperrt einzelne OP-Zeilen nicht. Parallele konkurrierende Zahlungen sind deshalb dort nicht durch dieselbe Sperrgarantie abgesichert wie unter PostgreSQL.
- Storno, Korrektur, Rückzahlung, Sammelzahlung, Überzahlungsguthaben, Anzahlungen und OP-Abstimmung bleiben spätere Stufen.
- Export, Import, Sicherung, Wiederherstellung und Mandantenlöschung wurden entsprechend der Abgrenzung nicht angepasst.
