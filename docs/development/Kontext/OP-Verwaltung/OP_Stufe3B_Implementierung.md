# OP-Verwaltung – Implementierungsstufe 3B

Stand: 26.10.2026
Ausgangspunkt: Commit `ac64ed1`
Status: Implementierung uncommitted; kein Commit erstellt.

## Umfang und Ergebnis

Eine tatsächliche Kunden- oder Lieferantenzahlung kann nun mehrere offene Rechnungs-OPs desselben Geschäftspartners und derselben Zahlungsrichtung ausgleichen. Der Benutzer legt je Rechnung den Zuordnungsbetrag fest. Vor der Buchung zeigt die Oberfläche die Zuordnungen zur ausdrücklichen Bestätigung an.

Die Summe der Zuordnungen muss exakt dem Zahlungsbetrag entsprechen. Jede einzelne Zuordnung wird gegen den aktuell offenen OP-Rest geprüft. Doppelte OPs innerhalb einer Zahlung, fremde Partner oder Mandanten, falsche Zahlungsrichtungen, überhöhte Einzelzuordnungen, Nullbeträge und nicht passende Summen werden abgelehnt. Es werden weder Restguthaben noch automatische Zuordnungen erzeugt.

Die Zahlung erzeugt eine Hauptbuchbuchung mit genau einer Bank-/Kassenzeile über den Gesamtbetrag und je OP eine Forderungs- beziehungsweise Verbindlichkeitszeile in Höhe seiner Zuordnung. Für jedes OP wird genau ein unveränderliches Ereignis gespeichert; alle Ereignisse referenzieren denselben Zahlungsdatensatz. Buchung, Zahlung und sämtliche Ereignisse werden in einer Session mit einem Commit gespeichert und bei Fehlern gemeinsam zurückgerollt. Die Einzelzahlungs-Methode aus Stufe 3A bleibt erhalten und verwendet denselben Ablauf mit einer Zuordnung.

## Schemaänderung

Die Stufe-3A-Tabelle `rechnungs_op_zahlungsereignisse` hatte `payment_id` als eindeutig markiert. Die neue Alembic-Migration `cf6b9217da40` entfernt diese Eindeutigkeit und ersetzt sie durch einen nicht eindeutigen Index. Die Einmaligkeit der Zahlung selbst bleibt über `zahlungen.payment_id` und die eindeutige Hauptbuchreferenz erhalten. Der Datenbank-Constraint stellt weiterhin sicher, dass die Zahlungsrichtung zum gesetzten Forderungs- oder Verbindlichkeits-OP-Fremdschlüssel passt.

## Geänderte OP-Dateien

- `src/simpleob/domain/open_item_payment.py` – bestehende Domänenobjekte weiterverwendet.
- `src/simpleob/database/models.py` – `payment_id` der Zuordnungsereignisse nicht mehr eindeutig; Index bleibt.
- `src/simpleob/database/open_item_payment_repository.py` – mehrere Ereignisse pro Zahlung atomar speichern und alle OPs sowie Partner/Richtung/Beträge erneut validieren.
- `src/simpleob/services/open_item_payment_service.py` – kompatibler Einzelzahlungsweg plus `post_payment_allocations` für exakte Mehrfachzuordnung und mehrzeilige Kontrollkontierung.
- `src/simpleob/ui_qt/open_item_payment_dialog.py` – Filter nach Richtung und Geschäftspartner, explizite Betragseingabe je offener Rechnung, Summenprüfung und Bestätigungsdialog.
- `migrations/versions/cf6b9217da40_allow_multiple_open_item_allocations.py` – Eindeutigkeitsänderung für SQLite und PostgreSQL.
- `tests/database/test_migration_service.py` – neue Alembic-Head-Revision.
- `tests/integration/test_open_item_payment.py` – Sammelzahlungen für Kunden und Lieferanten, Kombination von Voll- und Teilzuordnung, Fehlersummen, Doppelauswahl, Partner-/Mandantentrennung, Einzelüberzahlung und atomarer Rollback.
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe3B_Implementierung.md` – dieser Bericht.

Unabhängige Arbeitsbaumänderungen, insbesondere Benutzerhandbuch, PostgreSQL-Benutzerverwaltung, Datenbankkonfigurationsdialog und ältere Kontextdokumente, wurden nicht bearbeitet.

## Prüfungen

Ausgeführt wurden die Zahlungsintegrationstests, die OP-Regressionssuiten für Ausgangsrechnungen, Eingangsrechnungen und Gutschriften, der persistierte Hauptbuchworkflow, BookingRepository- und VAT-Service-Tests sowie die lokale Migrationstestgruppe ohne PostgreSQL-Tests.

Ergebnis: **61 Tests bestanden, 15 PostgreSQL-Tests ausgelassen**. Ruff und `git diff --check` sind erfolgreich. Die SQLite-Migrationskette einschließlich der neuen Migration wurde durch die Migrationstests geprüft. PostgreSQL wurde in dieser Stufe nicht praktisch getestet; die bekannte Testumgebung benötigt Datenbankzugangsdaten.

## Einschränkungen

- Sammelzahlungen sind auf einen Mandanten, einen Geschäftspartner und eine Zahlungsrichtung begrenzt.
- Eine Zahlung kann je OP nur eine Zuordnung enthalten; ein OP darf innerhalb derselben Zahlung nicht doppelt vorkommen.
- Überzahlungen, Guthabenbildung, Gutschriftenverrechnung, Anzahlungen, Rückzahlungen, automatische Zuordnungsvorschläge und Storno-/Korrekturworkflows bleiben außerhalb des Umfangs.
- Export, Import, Sicherung, Wiederherstellung und Mandantenlöschung wurden nicht verändert.
