# SimpleOB – Implementierungsstufe 2A

## Ergebnis

Stufe 2A ergänzt die Zielerfassung von Eingangsrechnungen mit einer
Lieferantenverbindlichkeit als OP. Sie verwendet die bestehende
`VatBookingService`-Logik für Eingangsrechnungen und die bereits vorhandene
`Buchung.booking_id` als Hauptbuchreferenz. Die Hauptbuchbuchung,
Eingangsrechnung und der Verbindlichkeits-OP werden über dieselbe
SQLAlchemy-Session gespeichert und durch einen gemeinsamen Commit bestätigt.
Bei einem Fehler im Persistenzablauf wird die Session zurückgerollt.

## Änderungen

- Neue Domänenobjekte für Eingangsrechnung und Verbindlichkeits-OP einschließlich
  positiver, normalisierter Ursprungsbeträge.
- Neues Repository mit Mandanten-, Lieferanten-, Geschäftsjahres-, Buchungs-
  und Duplikatprüfung. Dieselbe Rechnungsnummer bei demselben Lieferanten wird
  ohne Begründung abgewiesen; bei tatsächlichem Duplikat wird eine nichtleere
  Begründung gespeichert. Eine Begründung ohne Duplikat wird abgewiesen.
- Neuer Posting-Service, der `VatBookingService.build_input_booking` aufruft
  und Buchung, Rechnung sowie OP atomar persistiert.
- Neue mandantenspezifische Kontenrolle `SUPPLIER_PAYABLES`, samt Prüfung auf
  genau ein aktives Passivkonto und Integration in die vorhandene
  Kontenkonfiguration.
- Die vorhandene Rechnungserfassung kann bei Eingangsrechnungen „auf Ziel“
  erfassen und zeigt Lieferanten der Lieferantenrolle. Beim Duplikat erhält der
  Anwender eine Warnung und kann eine Begründung eingeben.
- Alembic-Migration `7c1f88e4d593` ergänzt `eingangsrechnungen` und
  `verbindlichkeits_ops`. Der Migrationstest wurde auf diese Head-Revision
  aktualisiert.

Geänderte beziehungsweise neu angelegte OP-Dateien:

- `src/simpleob/domain/payable_invoice.py`
- `src/simpleob/database/models.py`
- `src/simpleob/database/payable_invoice_repository.py`
- `src/simpleob/services/payable_invoice_posting_service.py`
- `src/simpleob/domain/accounting_account_roles.py`
- `src/simpleob/database/chart_of_accounts_repository.py`
- `src/simpleob/database/business_partner_repository.py`
- `src/simpleob/ui_qt/account_configuration_dialog.py`
- `src/simpleob/ui_qt/vat_booking_frame.py`
- `src/simpleob/ui_qt/main_window.py`
- `src/simpleob/qt_main.py`
- `migrations/versions/7c1f88e4d593_add_supplier_invoice_open_items.py`
- `tests/database/test_migration_service.py`
- `tests/integration/test_payable_invoice_posting.py`

## Geprüfte Eigenschaften

Die fokussierten Tests prüfen erfolgreiche Buchung und OP-Eröffnung,
Rückabwicklung bei einem Fehler nach dem OP-Staging, Fremdmandanten,
Geschäftsjahre, fehlende oder ungeeignete Kontenrollen, Speicherung und
Freigabegrund bei Rechnungsnummer-Duplikaten sowie die Migration. Die
Kontenrollen-Persistenz wird ebenfalls geprüft.

Die bestehende Ausgangsrechnung auf Ziel sowie Buchungsrepository,
Kontenrollen-Repository und Umsatzsteuer-Buchungsservice wurden in den
fokussierten Regressionstests mit ausgeführt. Der UI-Dublettenpfad wurde
zusätzlich mit einem Offscreen-Dialog-Smoke-Check geprüft.

## Testergebnisse

- Fokussierte OP-, Ausgangsrechnungs-, Migrations-, Buchungs-, Kontenrollen-
  und Umsatzsteuer-Tests sowie UI-Suite: **85 bestanden, 1 ausgelassen**.
- Ausgelassen wurde `postgresql_connection_is_checked`, da dieser Test einen
  nativen Zugangsdialog öffnet und im headless Lauf blockieren kann.
- `ruff check` für die geänderten OP-Dateien: **bestanden**.
- `git diff --check`: **bestanden**.
- Ein PostgreSQL-Lauf wurde nicht durchgeführt; die ausgeführte
  Migrationstestumgebung war SQLite.

## Abgrenzung und offene Einschränkungen

Zahlungen, Gutschriften, Anzahlungen, §-19-Automatik und OP-Abstimmung sind
nicht Teil dieser Stufe. Mandantenexport, Import, Sicherung, Wiederherstellung
und Löschung bleiben wie vereinbart für später zurückgestellt. E-Bilanz/ERiC
wurde nicht geändert.

Eine Rechnungsnummerndublette wird in dieser Stufe in der Repository-Prüfung
festgestellt und eine begründete erneute Erfassung gespeichert. Eine
gleichzeitige konkurrierende Erfassung derselben Nummer ist mangels
Eindeutigkeitsconstraint nicht datenbankseitig serialisiert und bleibt ein
technischer Grenzfall für spätere Abstimmungs-/Nebenbucharbeiten.

Es wurde kein Commit erstellt. Vorbestehende unabhängige Änderungen im
Arbeitsbaum (unter anderem PostgreSQL-Benutzerverwaltung und Benutzerhandbuch)
wurden nicht Bestandteil dieser Implementierung und bleiben unberührt.
