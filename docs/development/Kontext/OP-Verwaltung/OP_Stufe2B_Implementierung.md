# SimpleOB – OP-Verwaltung, Implementierungsstufe 2B

## Ergebnis

Die OP-Erfassung verarbeitet Kunden- und Lieferantengutschriften als eigene
gebuchte Nebenbuchbelege. Jede Gutschrift erzeugt genau eine Hauptbuchbuchung,
einen Gutschriftbeleg und einen Guthaben-OP innerhalb derselben SQLAlchemy-
Transaktion. Die Buchungserzeugung delegiert an die vorhandenen Methoden
`VatBookingService.build_customer_credit_note()` beziehungsweise
`build_supplier_credit_note()`; die Steuer- und Kontierungslogik des
Umsatzsteuerdienstes blieb unverändert.

Für Kundenguthaben ist ein mandantenspezifisches Passivkonto, für
Lieferantenguthaben ein mandantenspezifisches Aktivkonto vorgesehen. Die
Kontonummern stammen ausschließlich aus der Konfiguration. Speicherung und
Buchung werden bei Fehlern gemeinsam zurückgerollt.

## Fachliche und technische Umsetzung

- `Gutschrift` speichert Mandant, Geschäftspartner, Gutschriftart, Nummer,
  Belegdatum, Buchungsreferenz und optional den Bezug auf eine Rechnung.
  Kundenbezüge verweisen auf eine Ausgangsrechnung, Lieferantenbezüge auf eine
  Eingangsrechnung. Die Prüfung bindet Bezug, Partner und Mandant zusammen.
- `GuthabenOP.amount` ist der gespeicherte unveränderliche Ursprungsbetrag.
  Einen frei änderbaren Guthabensaldo gibt es nicht. `get_open_amount()`
  berechnet den offenen Betrag aus Ursprungsbetrag plus signierten
  `GuthabenOPEreignis`-Beträgen.
- Kundengutschriftnummern müssen mandantenweit eindeutig sein und kollidieren
  auch mit Ausgangsrechnungsnummern. Lieferantengutschriften folgen der
  Lieferantenregel aus Stufe 2A: gleiche Nummer beim selben Lieferanten löst
  eine Warnung aus; eine Wiedererfassung erfordert eine gespeicherte
  Begründung. Dabei werden auch Eingangsrechnungen desselben Lieferanten
  berücksichtigt.
- Die vorhandene Umsatzsteuer-Erfassung zeigt bei Gutschriften den passenden
  Geschäftspartner, die Gutschriftnummer und ein optionales Feld für die
  ursprüngliche Rechnungsnummer. Die Rechnungsnummer wird zu einer eindeutigen,
  partner- und mandantengebundenen Referenz aufgelöst. Lieferantendubletten
  können nach Warnung mit Begründung erneut erfasst werden.
- Die Migration `8f32c0a94b1e` ergänzt `gutschriften`, `guthaben_ops` und
  `guthaben_op_ereignisse` einschließlich Mandanten-/Partner-, Buchungs-,
  Rechnungs- und Betragsconstraints. Die vorhandene generische Tabelle für
  Kontenrollen erhält die Rollen `CUSTOMER_CREDIT_BALANCES` und
  `SUPPLIER_CREDIT_BALANCES`; eine eigene Rollenmigration ist nicht nötig.
- Der Guthaben-OP wird in dieser Stufe nur eröffnet. Es gibt keine Zahlung,
  Rückzahlung, Verrechnung oder zusätzliche Geldbewegung. Ereignisse können
  bei der Restbetragsberechnung berücksichtigt werden; ein Workflow zum
  Erzeugen künftiger Ausgleichsereignisse gehört nicht zu 2B.

## Geänderte und neue Dateien

- `src/simpleob/domain/accounting_account_roles.py`
- `src/simpleob/domain/credit_note.py`
- `src/simpleob/database/models.py`
- `src/simpleob/database/chart_of_accounts_repository.py`
- `src/simpleob/database/credit_note_repository.py`
- `src/simpleob/services/credit_note_posting_service.py`
- `src/simpleob/ui_qt/account_configuration_dialog.py`
- `src/simpleob/ui_qt/vat_booking_frame.py`
- `src/simpleob/ui_qt/main_window.py`
- `src/simpleob/qt_main.py`
- `migrations/versions/8f32c0a94b1e_add_credit_notes_and_credit_open_items.py`
- `tests/database/test_migration_service.py`
- `tests/integration/test_credit_note_posting.py`

`VatBookingService`, die E-Bilanz-/ERiC-Funktionen, Export/Import,
Sicherung/Wiederherstellung und Mandantenlöschung wurden nicht geändert.

## Tests und Prüfungen

- OP-, Migrations-, Kontenrollen-, Buchungs- und Umsatzsteuer-Regressionen
  einschließlich Stufe 1 und 2A, SQLite: **58 bestanden, 15 PostgreSQL-
  bezogene Tests herausgefiltert**.
- UI-Suite headless: **39 bestanden, 1 nativer PostgreSQL-Verbindungsdialogtest
  ausgelassen**.
- Zusätzlicher Offscreen-Smoke-Check: Kundengutschrift über den Dialogpfad
  wird an den Guthaben-OP-Callback übergeben; Supplier-Duplikat zeigt Warnung,
  fragt eine Begründung ab und wiederholt den Aufruf.
- `ruff check`, `compileall` und `git diff --check`: **bestanden**.

Ein zusätzlich unfiltrierter Migrations-Testlauf ergab 65 bestandene und 8
fehlgeschlagene PostgreSQL-bezogene Tests. Die Verbindungsprüfungen scheiterten
mit „Operation not permitted“ beim lokalen PostgreSQL-Zugriff. Ein
Mock-basierter PostgreSQL-Test scheiterte außerdem an einer bestehenden
Test-Doppelgängerfunktion, die das inzwischen verwendete `connect_args`
Keyword nicht annimmt. Die neue Migration wurde daher in SQLite, nicht in
PostgreSQL ausgeführt.

## Offene Einschränkungen

- PostgreSQL-Migration und -Constraints müssen noch in einer erreichbaren
  PostgreSQL-Testumgebung geprüft werden.
- Die Ereignistabelle wird in 2B nicht durch Zahlungs-, Verrechnungs- oder
  Rückzahlungsworkflows befüllt. Der Restbetrag ist jedoch für vorhandene
  Ereigniszeilen berechenbar.
- Direkte Änderungen an Datenbankzeilen werden nicht durch Trigger gesperrt;
  die Anwendung stellt für gebuchte Gutschriften und Guthaben-OPs keine
  Änderungsfunktion bereit.
- §-19-Automatik, Anzahlungen, allgemeine OP-Abstimmung sowie die Integration
  in Mandantenexport/-import, Sicherung/Wiederherstellung und Löschung bleiben
  wie vereinbart außerhalb dieser Stufe.

Es wurde kein Commit erstellt. Vorbestehende unabhängige Änderungen im
Arbeitsbaum – darunter PostgreSQL-Benutzerverwaltung und Benutzerhandbuch –
blieben unangetastet.
