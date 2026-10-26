# OP-Verwaltung – Implementierungsstufe 3C

Stand: 26.10.2026
Ausgangspunkt: Commit `bda0cef`
Status: Implementierung uncommitted; kein Commit erstellt.

## Umfang und Ergebnis

Die manuelle Verrechnung eines Kunden- oder Lieferantenguthabens mit genau einem Rechnungs-OP ist implementiert. Der Benutzer wählt Richtung, Geschäftspartner, Rechnungs-OP, Guthaben-OP und Betrag ausdrücklich aus und bestätigt die Verrechnung vor dem Buchen. Mehrfachverrechnungen als Sammelvorgang sind nicht enthalten; mehrere zeitlich getrennte Teilverrechnungen derselben beiden OPs sind möglich.

Eine Verrechnung wird nur akzeptiert, wenn beide OPs demselben Mandanten, Geschäftspartner und der passenden Kunden- oder Lieferantenrichtung angehören. Der Betrag muss positiv sein und darf weder den offenen Rechnungsrest noch das verfügbare Guthaben übersteigen.

Kundenseite: Kundenguthabenkonto im Soll, Kundenforderungskonto im Haben. Lieferantenseite: Lieferantenverbindlichkeitskonto im Soll, Lieferantenguthabenkonto im Haben. Die bebuchten Konten werden aus den ursprünglichen Hauptbuchbuchungen der beiden OPs ermittelt. Es wird keine Bank- oder Kassenzeile erzeugt.

Hauptbuchbuchung, Verrechnungskopf und je ein Rechnungs- und Guthabenereignis werden in derselben SQLAlchemy-Transaktion gespeichert. Beide Ereignisse verweisen über dieselbe Verrechnungs-ID aufeinander. Das Rechnungsereignis reduziert den offenen Rechnungsbetrag; das Guthabenereignis erhält eine negative Betragsänderung und reduziert damit das verfügbare Guthaben. Verrechnungsdatum, Buchungsdatum, Erfassungszeitpunkt, OP-Referenzen und Hauptbuchreferenz werden getrennt dokumentiert.

Die gemeinsame Restberechnung berücksichtigt nun sowohl Zahlungen als auch Rechnungsverrechnungen. `CreditNoteRepository.get_open_amount()` berücksichtigt die Verrechnung über dieselben Guthabenereignisse wie die bisherige Ereignisberechnung. Dadurch bleiben Zahlungserfassung, Verrechnungsauswahl und Guthabenauswahl auf dem gleichen berechneten Stand.

## Geänderte Dateien

- `src/simpleob/domain/open_item_offset.py` – Verrechnungsrichtung, OP-Summaries und unveränderlicher Verrechnungsvorgang.
- `src/simpleob/database/models.py` – Verrechnungskopf, Rechnungsereignis und Verknüpfung des Guthabenereignisses mit dem Verrechnungsvorgang.
- `src/simpleob/database/open_item_offset_repository.py` – OP-Restberechnung, Mandanten-/Partnerprüfung, Ermittlung der tatsächlich bebuchten Ursprungskonten und atomare Speicherung.
- `src/simpleob/database/open_item_payment_repository.py` – Rechnungsrest berücksichtigt zusätzlich die Verrechnungsereignisse.
- `src/simpleob/services/open_item_offset_service.py` – Betragsprüfung, Soll-/Haben-Erzeugung und atomarer Haupt-/Nebenbuchablauf.
- `src/simpleob/ui_qt/open_item_offset_dialog.py` – Auswahl und Bestätigung einer einzelnen Verrechnung.
- `src/simpleob/ui_qt/main_window.py`, `src/simpleob/qt_main.py` – Schaltfläche und Serviceverdrahtung.
- `migrations/versions/4b7f2a90c1de_add_open_item_credit_offsets.py` – Schemaerweiterung für SQLite und PostgreSQL.
- `tests/database/test_migration_service.py` – aktualisierte Alembic-Head-Revision.
- `tests/integration/test_open_item_offset.py` – Kunden-/Lieferantenfälle, Teil- und Vollverrechnung, Zahlungszusammenspiel, Kontierung, Integrität, Überverrechnung und Rollback.
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe3C_Implementierung.md` – dieser Bericht.

Unabhängige Änderungen an Benutzerhandbuch, PostgreSQL-Benutzerverwaltung, Datenbankkonfigurationsdialog und älteren Kontextdokumenten wurden nicht bearbeitet.

## Prüfungen

Ausgeführt wurden die neuen Verrechnungstests, die Zahlungsregressionen aus 3A/3B, Ausgangs-/Eingangsrechnungs- und Gutschriftenintegrationstests, der persistierte Hauptbuchworkflow, BookingRepository- und VAT-Service-Tests sowie die Migrationstestgruppe ohne PostgreSQL-Tests.

Ergebnis: **66 Tests bestanden, 15 PostgreSQL-Tests ausgelassen**. Ruff und `git diff --check` sind erfolgreich. Die SQLite-Migrationskette einschließlich der Verrechnungs-Migration wurde durch Migrationstests geprüft. PostgreSQL konnte wegen der bekannten fehlenden Zugangsdaten nicht praktisch verifiziert werden.

## Verbleibende Einschränkungen

- Es wird jeweils nur ein Rechnungs-OP mit einem Guthaben-OP verrechnet.
- Es gibt keine automatische Verrechnung, Rückzahlung, Überzahlungsguthaben, Anzahlungen oder Storno-/Korrekturworkflows.
- Die PostgreSQL-Migration und Transaktion wurden in dieser Umgebung nicht praktisch getestet.
- Mandantenexport, Import, Sicherung, Wiederherstellung und Löschung bleiben unverändert.
