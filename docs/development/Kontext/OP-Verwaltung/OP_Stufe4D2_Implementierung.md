# Stufe 4D-2 – Stornierung unbezahlter Kunden- und Lieferantenrechnungen

## Ergebnis

Die OP-Verwaltung kann unbezahlte Kunden- und Lieferantenrechnungen vollständig stornieren. Der Vorgang ist auf Rechnungen beschränkt, deren Originalbuchung im ausgewählten offenen Geschäftsjahr liegt. Jede Zahlungs-, Verrechnungs- oder Zahlungszuordnungskorrekturhistorie sperrt das Storno. Ursprungsrechnung und Ursprungsbuchung bleiben unverändert.

Die Gegenbuchung übernimmt alle gespeicherten Originalbuchungszeilen mit vertauschter Soll-/Haben-Seite, verwendet `BookingType.REVERSAL` und referenziert die Originalbuchung über `reversal_of_booking_id`. Sie wird gemeinsam mit dem OP-Stornodatensatz in einer SQLAlchemy-Transaktion gespeichert. Es wird keine Zahlung und keine Bank- oder Kassenbuchung erzeugt.

## Abschließende technische Nachprüfung

### PostgreSQL-Kompatibilität und Laufzeitprüfung

Die Migration und das SQLAlchemy-Modell verwenden PostgreSQL-kompatible `INTEGER`, `VARCHAR`, `NUMERIC(18,2)`, `DATE`, `TIMESTAMP WITH TIME ZONE`-äquivalente sowie benannte Constraints. Der zusammengesetzte Fremdschlüssel `(mandant_id, partner_id)` referenziert exakt das in der früheren Migration `4ad7f6e0c31b` angelegte eindeutige Schlüsselpaar der Geschäftspartner. Die einzelnen Fremdschlüssel referenzieren jeweils eindeutige IDs (`invoice_id`, `open_item_id`, `booking_id`). Die einzelnen `UNIQUE`-Constraints auf den optionalen Kunden-/Lieferantenreferenzen sind auf SQLite und PostgreSQL mit mehrfachen `NULL`-Werten kompatibel. `length(trim(reason)) > 0`, der Richtungs-Check und `amount > 0` sind auf beiden Datenbanken gültige Check-Ausdrücke.

### Indexnamen der Zahlungszuordnungskorrekturereignisse

Die Migration `7d0c4a28b9f1` enthielt bislang `ix_zahlungszuordnungskorrekturereignisse_receivable_open_item_id` (64 ASCII-Zeichen) und `ix_zahlungszuordnungskorrekturereignisse_payable_open_item_id` (61 ASCII-Zeichen). Nur der erste Name überschritt tatsächlich PostgreSQLs 63-Byte-Grenze; beide Namen wurden auf kurze, eindeutige Namen geändert:

| Zweck | Alt | Neu |
|---|---|---|
| Kunden-OP-Ereignisse | `ix_zahlungszuordnungskorrekturereignisse_receivable_open_item_id` | `ix_zukorr_evt_receivable_open_item` |
| Lieferanten-OP-Ereignisse | `ix_zahlungszuordnungskorrekturereignisse_payable_open_item_id` | `ix_zukorr_evt_payable_open_item` |

Die gleichen Namen sind nun im Modell `Zahlungszuordnungskorrekturereignis` definiert. Auf der geprüften vorhandenen SQLite-Datei `data/openbilanz.db` (Alembic-Revision `c71f4db9e2a6`) waren die alten Namen tatsächlich gespeichert. `data/openbilanz-before-migration.db` steht auf `3d5f3f742f56`; `openbilanz.db` und `data/openbilanz.standalone.db` haben keine passende OP-Korrekturtabelle. Die Änderung der Indexnamen ändert weder Spalten noch Indexfunktion. Der Downgrade der Migration ermittelt deshalb den existierenden Namen und entfernt wahlweise den neuen oder den alten Namen; so bleibt auch ein Downgrade einer bereits mit der alten Fassung migrierten SQLite-Datei möglich. Spätere Migrationen referenzieren diese Indexnamen nicht.

Die ausdrücklich freigegebene Testdatenbank `simpleob_migration_test` wurde vor der Änderung und unmittelbar vor dem Upgrade geprüft. Auf `::1:5432` war die tatsächliche Identität `simpleob_migration_test` / `simpleob_auth_test`. `USAGE` und `CREATE` auf `public`, `REFERENCES` auf `public.mandanten` und `public.buchungen` sowie `UPDATE` auf `public.alembic_version` waren vorhanden. Ausgangsrevision war `3d5f3f742f56`; das Upgrade wurde bis zum Quellcode-Head `d4a2f19c7b60` ausgeführt und nach Verlassen der Migrationsverbindung persistent gegengeprüft.

Ein erster erfolgreicher Alembic-Aufruf fand zunächst innerhalb einer bereits durch Identitätsabfragen geöffneten SQLAlchemy-Transaktion statt; beim Schließen der Verbindung wurde diese äußere Transaktion zurückgerollt. Die anschließende Leseprüfung deckte das auf. Der abschließende Lauf schloss die reine Vorab-Lese-Transaktion vor Alembic, führte das Upgrade erneut aus und bestätigte die persistierte Head-Revision. Es wurde ausschließlich `simpleob_migration_test` verändert.

PostgreSQL bestätigte die Tabelle `public.rechnungs_op_stornos`, alle zwölf erwarteten Spalten, sieben Fremdschlüssel (einschließlich des zusammengesetzten Mandanten-/Partner-FKs), sechs Unique-Constraints und drei Check-Constraints. Die Tabelle enthält keine unerwarteten Indexanforderungen. Die beiden gekürzten Ereignisindizes sind in `public.zahlungszuordnungskorrekturereignisse` mit den erwarteten Spalten vorhanden.

### Atomare Persistenz und Journalsperre

Der produktive Schreibpfad ist `OpenItemInvoiceCancellationService.cancel_invoice()` → `OpenItemInvoiceCancellationRepository.add_atomic()`. Die Methode legt Gegenbuchung und Stornodatensatz mit `Session.add_all()` in derselben Session an, führt genau einen `flush()` und anschließend genau einen gemeinsamen Commit über `BookingRepository.commit()` aus. Ein Fehler innerhalb des Schreibpfads führt über `BookingRepository.rollback()` zum vollständigen Rollback. Vorschau und Validierung committen nicht.

`BookingRepository.add()` behält die 4D-1-Sperre für OP-Ursprungsbuchungen. Der Spezialpfad verwendet keinen allgemeinen Freigabeparameter und stellt keine Methode bereit, die nur eine OP-Gegenbuchung speichert: `add_atomic()` prüft die fachlichen Voraussetzungen selbst und schreibt stets sowohl Hauptbuchgegenbuchung als auch Stornodatensatz. Die vorhandene `FiscalYearWorkspace`- und Journalstorno-Verarbeitung wird nicht freigegeben.

### Konkurrenztest

Der Test `test_concurrent_invoice_cancellation_leaves_one_complete_reversal` verwendet eine dateibasierte SQLite-Testdatenbank und zwei unabhängig angelegte SQLAlchemy-Sessions. Eine Barriere hält beide Versuche nach erfolgreicher erneuter Zulassungsprüfung an, bis beide dort angekommen sind; anschließend setzen sie die Schreibvorgänge überlappend fort. Der Test prüft, dass genau ein Vorgang erfolgreich ist und genau ein Stornodatensatz sowie eine Gegenbuchung verbleiben. Damit bildet er einen tatsächlichen konkurrierenden SQLite-Fall ab, nicht bloß zwei sequenzielle Aufrufe. Er belegt keine PostgreSQL-Laufzeitsemantik.

### Migration und Downgrade

Der vollständige Alembic-Downgrade-Lauf protokolliert zuerst den erfolgreichen Downgrade `d4a2f19c7b60 → c71f4db9e2a6` einschließlich des Entfernens der neuen Tabelle. Erst später scheitert er beim Downgrade der älteren Migration `cf6b9217da40` an deren bereits vorhandener nicht benannter Unique-Constraint. Die neue Migration ist damit aktualisier- und rücknehmbar; eine Änderung an `cf6b9217da40` ist für Stufe 4D-2 weder erforderlich noch Teil des Umfangs.

## Datenmodell und Migration

Neu ist `RechnungsOPStorno` in `src/simpleob/database/models.py`. Der Datensatz enthält Storno-ID, Mandant, Geschäftspartner, genau eine Kunden- oder Lieferantenrechnung samt zugehörigem Rechnungs-OP, Hauptbuchgegenbuchung, positiven Ursprungsbetrag, Erfassungszeitpunkt und verpflichtenden Stornogrund.

Check-Constraints erzwingen genau eine Belegart, einen positiven Betrag und einen nichtleeren Grund. Eindeutige Constraints verhindern ein zweites Storno derselben Rechnung beziehungsweise desselben OPs und die Wiederverwendung einer Stornobuchung. Der zusammengesetzte Fremdschlüssel schützt den Mandanten-/Geschäftspartnerbezug; die übrigen Fremdschlüssel verweisen auf bestehende Belege, OPs und Hauptbuchbuchungen.

Die Migration `migrations/versions/d4a2f19c7b60_add_unpaid_invoice_open_item_stornos.py` hängt an `c71f4db9e2a6`. Sie erstellt ausschließlich die neue Tabelle; bestehende Daten werden nicht verändert. SQLite-Migrationstests liefen erfolgreich. PostgreSQL wurde von `3d5f3f742f56` bis einschließlich `d4a2f19c7b60` migriert.

## Autorisierter Buchungsweg und Transaktion

`OpenItemInvoiceCancellationService` stellt Vorschau und Ausführung bereit. `OpenItemInvoiceCancellationRepository.add_atomic()` prüft die Voraussetzungen beim Schreiben erneut und speichert Gegenbuchung und Stornodatensatz gemeinsam. Der allgemeine `BookingRepository.add()` bleibt unverändert gegen das isolierte Journalstorno von OP-Ursprungsbuchungen gesperrt; es gibt keinen frei wählbaren Freigabeparameter. Der spezielle Repository-Weg schreibt erst nach seiner eigenen vollständigen Prüfung direkt in dieselbe Session.

Die Prüfung umfasst:

- Mandant, Partnerrolle, Rechnung und Rechnungs-OP;
- offenes Zielgeschäftsjahr und Buchungsdatum innerhalb dieses Jahres;
- Originalbuchung im selben Geschäftsjahr und innerhalb dessen Datumsspanne;
- regulären Buchungstyp, mindestens zwei vorhandene Zeilen, ausgeglichene Soll-/Haben-Summen und mandanteneigene Konten;
- fehlende frühere Gegenbuchung oder Stornierung;
- keinerlei Zahlungs-, Verrechnungs- oder Korrekturhistorie, auch wenn diese historisch neutralisiert wäre.

Das Geschäftsjahr wird mit dem vorhandenen Lockmechanismus des `BookingRepository` gesperrt; auf PostgreSQL wird zusätzlich der Rechnungs-OP mit `FOR UPDATE` gesperrt. SQLite bietet diese Zeilensperre nicht. Die eindeutigen Storno-Constraints bilden dort und als zusätzliche PostgreSQL-Sicherung die letzte Barriere: Bei einem konkurrierenden Konflikt wird die gesamte Transaktion einschließlich der Gegenbuchung zurückgerollt. Der dateibasierte SQLite-Konkurrenztest mit zwei getrennten Sessions und synchronisierter Zulassungsprüfung ist vorhanden. PostgreSQL-spezifisches Parallelverhalten wurde nicht durch zwei parallele PostgreSQL-Sessions getestet.

## OP-Berechnung, Übersicht und Abstimmung

`OpenItemPaymentRepository.get_open_invoice()` zieht den stornierten Ursprungsbetrag vom offenen Rechnungsbetrag ab. Dadurch werden nachträgliche Zahlungen und Verrechnungen auf den geschlossenen OP abgewiesen. `OpenItemOverviewRepository` zeigt den Restbetrag als 0,00 €, sodass der Posten aus „Nur offene Posten“ entfällt und in „Alle Posten“ sichtbar bleibt. Die Ereignisdetails zeigen ein Rechnungsstorno mit Belegnummer, Buchungsdatum, Betrag, Grund und lesbarem Gegenbuchungshinweis; die interne UUID wird nicht als Beschreibung ausgegeben.

`OpenItemReconciliationRepository` berücksichtigt die OP-Minderung erst, wenn das Buchungsdatum der Gegenbuchung erreicht ist. Vor diesem Datum bleibt der historische OP-Betrag bestehen. Die Gegenbuchung wird als bekannte OP-Bewegung markiert und erscheint nicht als ungeklärte Sammelkontozeile.

## Oberfläche

`OpenItemOverviewWidget` erhält die Aktion „Rechnung vollständig stornieren“. Sie ist nur für offene Rechnungs-OPs aktiv. Die Oberfläche prüft zunächst die Stornierbarkeit, fragt danach Stornobuchungsdatum und verpflichtenden Grund ab und zeigt die gespiegelt dargestellten Buchungszeilen sowie das Schließen des OPs in einer ausdrücklichen Bestätigungsabfrage an. Nach Bestätigung werden OP-Übersicht, Journal, Konten- und Abschlussanzeigen aktualisiert. Die allgemeine Journal-Stornierung bleibt eine getrennte Funktion.

Die Anwendung verdrahtet den Service in `src/simpleob/qt_main.py`; `MainWindow` bindet ihn in der OP-Übersicht ein und aktualisiert die Hauptbuchanzeigen nach erfolgreichem Storno.

## Geänderte Dateien

- `src/simpleob/database/models.py`
- `src/simpleob/database/booking_repository.py`
- `src/simpleob/database/open_item_invoice_cancellation_repository.py` (neu)
- `src/simpleob/domain/open_item_invoice_cancellation.py` (neu)
- `src/simpleob/services/open_item_invoice_cancellation_service.py` (neu)
- `src/simpleob/domain/open_item_overview.py`
- `src/simpleob/database/open_item_payment_repository.py`
- `src/simpleob/database/open_item_overview_repository.py`
- `src/simpleob/database/open_item_reconciliation_repository.py`
- `src/simpleob/ui_qt/open_item_overview_widget.py`
- `src/simpleob/ui_qt/main_window.py`
- `src/simpleob/qt_main.py`
- `migrations/versions/7d0c4a28b9f1_add_payment_allocation_corrections.py` (PostgreSQL-kompatible Indexnamen und abwärtskompatibler Downgrade)
- `migrations/versions/d4a2f19c7b60_add_unpaid_invoice_open_item_stornos.py` (neu)
- `tests/integration/test_open_item_overview.py`
- `tests/ui/test_open_item_overview_widget.py`
- `tests/database/test_migrations.py`
- `tests/database/test_migration_service.py`

Die beiden Migrationstests wurden nur auf die neue Head-Revision aktualisiert.

## Tests und Prüfungen

Erfolgreich:

- Fokussierte OP-, Zahlungs-, Verrechnungs-, Korrektur-, Rechnungs-, Gutschriften-, Abstimmungs-, Journalstorno- und UI-Regressionstests mit dem zusätzlichen PostgreSQL-Funktionstest: **74 passed**. Der SQLite-Konkurrenztest bestätigte bei zwei getrennten Sessions genau ein erfolgreiches Storno. Der PostgreSQL-Funktionstest prüfte Kunden- und Lieferantenrechnung, Hauptbuchgegenbuchung und Stornodatensatz, Doppelstornoverhinderung, Fremdmandantabwehr und Rollback nach einem simulierten Flush-Fehler.
- SQLite-Migration von der Baseline bis zur neuen Head-Revision: **4 passed, 1 deselected** (nur der bekannte vollständige Downgrade-Test wurde ausgefiltert).
- Migrationsdiensttests ohne PostgreSQL-Tests: **7 passed, 15 deselected**.
- PostgreSQL-Migration: von `3d5f3f742f56` bis `d4a2f19c7b60`, erfolgreich und persistent verifiziert. Constraints der Stornotabelle und beide kurzen Ereignisindizes wurden über PostgreSQL-Inspector geprüft.
- Ruff für alle in dieser Prüfung geänderten Produktiv-, Migrations- und Testdateien: **erfolgreich**. `git diff --check`: **erfolgreich**.

Einschränkungen der Prüfungen:

- Der vollständige Downgrade-Test scheitert weiterhin in der älteren Migration `cf6b9217da40`, weil deren bestehende SQLite-Downgrade-Constraint keinen Namen hat. Die neue Migration selbst wurde beim Downgrade bis zu dieser älteren Fehlerstelle bereits erfolgreich zurückgenommen. Das Upgrade bis einschließlich der neuen Migration war erfolgreich.
- Ein PostgreSQL-spezifischer Konkurrenztest wurde nicht ergänzt oder ausgeführt. Der vorhandene echte Zweitsession-Konkurrenztest bleibt SQLite-basiert; der PostgreSQL-Funktionstest läuft absichtlich in einer rollback-fähigen Transaktion, während parallele unabhängige Sessions bestätigte Testdaten benötigen würden. PostgreSQL-Zeilensperrverhalten ist daher nicht zur Laufzeit belegt.
- Der vollständige Downgrade-Lauf bleibt an der bekannten älteren Migration `cf6b9217da40` hängen; der neue Index-Downgrade in `7d0c4a28b9f1` unterstützt sowohl die alten SQLite-Namen als auch die neuen gekürzten Namen.
- Ein zuvor ausgeführter repo-weiter `ruff check src/simpleob tests`-Lauf meldete 58 Findings außerhalb dieser Stufe. Sie wurden nicht bearbeitet; Ruff auf den tatsächlich geänderten Dateien ist sauber.

## Einschränkungen

Nicht enthalten sind Stornos bezahlter oder historisch zugeordneter Rechnungen, Gutschriftenstornos, Verrechnungsrücknahmen, jahresübergreifende Stornos, Forderungsabschreibungen sowie Anpassungen an E-Bilanz/ERiC und Mandantentransfer. Das PostgreSQL-Zeilensperrverhalten folgt dem vorhandenen `BookingRepository`-Lockmechanismus; es wurde in dieser Prüfung nicht durch zwei konkurrierende PostgreSQL-Sessions verifiziert.
