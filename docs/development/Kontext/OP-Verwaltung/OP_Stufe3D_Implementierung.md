# SimpleOB – OP-Verwaltung, Implementierungsstufe 3D

**Ausgangspunkt:** `83e08ef`
**Stand:** 26.10.2026
**Status:** Implementierung und fokussierte Prüfungen abgeschlossen; noch nicht committet.

## Umfang und Ergebnis

Die Stufe ergänzt eine manuelle, begründete Korrektur einer bereits gebuchten Zuordnung zwischen einer Zahlung und einer Rechnung. Die Zahlung, ihre ursprüngliche Hauptbuchbuchung und das ursprüngliche Zahlungsereignis bleiben unverändert.

Eine Korrektur wird mit zwei neuen Ereignissen festgehalten: `SOURCE_RELEASE` entlastet die falsch zugeordnete Rechnung, `TARGET_APPLY` belastet die ausgewählte Zielrechnung. Korrekturen können teilweise und wiederholt erfolgen; ihre Gesamtsumme darf die ursprüngliche Zuordnung nicht überschreiten. Die Zielrechnung muss den Korrekturbetrag noch offen haben.

Wenn Quell- und Zielrechnung dasselbe tatsächliche Forderungs- beziehungsweise Verbindlichkeitskonto verwenden, wird keine Hauptbuchbuchung angelegt. Bei unterschiedlichen Konten entsteht eine ausgeglichene reine Umbuchung zwischen den beiden Konten. Dabei wird keine Bank- oder Kassenzeile erzeugt.

## Änderungen

- `src/simpleob/database/models.py`: Korrekturkopf und unveränderliche Korrekturereignisse mit Begründung, Zahlungs-/OP-Referenzen, Beträgen, Datum, Erfassungszeitpunkt und optionaler Hauptbuchreferenz. Constraints sichern positive Beträge, passende Richtung, Ereignisrollen und eindeutige Ereignisrollen je Korrektur.
- `migrations/versions/7d0c4a28b9f1_add_payment_allocation_corrections.py`: Alembic-Migration für beide Tabellen und Indizes; Folgerevision von `4b7f2a90c1de`.
- `src/simpleob/domain/payment_allocation_correction.py`: unveränderliche Korrektur- und noch-korrigierbare-Zuordnung-Datentypen; verpflichtende Begründung und positiver Betrag.
- `src/simpleob/database/payment_allocation_correction_repository.py`: Mandanten-, Partner-, Richtungs-, Ursprungszuordnungs- und Geschäftsjahresprüfung; Speicherung der Korrektur und beider OP-Ereignisse.
- `src/simpleob/database/open_item_payment_repository.py`: offene Rechnungsbeträge berücksichtigen nun zusätzlich die signierten Korrekturereignisse. Dadurch fließen Korrekturen auch in Zahlungs- und Verrechnungsabfragen konsistent ein.
- `src/simpleob/services/payment_allocation_correction_service.py`: Prüfung der noch korrigierbaren Summe und des Zielrests; Konten werden aus den ursprünglichen Buchungen beider Rechnungen ermittelt. Bei Kontenwechsel wird die Umbuchung mit `commit=False` zusammen mit den Nebenbuchdaten gespeichert und einmal gemeinsam bestätigt. Fehler führen zum Rollback.
- `src/simpleob/ui_qt/payment_allocation_correction_dialog.py`: Auswahl einer offenen ursprünglichen Zahlungszuordnung und einer Zielrechnung desselben Partners, Betrag, Korrekturdatum, Buchungsdatum, Pflichtbegründung sowie ausdrückliche Bestätigungsabfrage.
- `src/simpleob/ui_qt/main_window.py` und `src/simpleob/qt_main.py`: Serviceverdrahtung und Zugang über „Zahlungszuordnung korrigieren…“.
- `tests/integration/test_payment_allocation_correction.py`: Integrationstests für wiederholte Teilkorrekturen, Restbeträge, unveränderte Zahlung, Kontenumbuchung ohne Finanzkonto, Lieferantenrichtung, Pflichtbegründung und Rollback.
- `tests/database/test_migration_service.py`: erwartete Migrationsrevision auf `7d0c4a28b9f1` aktualisiert.

## Transaktion und Integrität

Der Korrekturservice verwendet die bestehende SQLAlchemy-Session des Buchungsrepositories. Bei abweichenden Sammelkonten wird die Umbuchung zuerst mit `commit=False` in dieselbe Session aufgenommen. Anschließend schreibt das OP-Repository den Korrekturkopf und beide Ereignisse ebenfalls ohne Commit. Ein gemeinsamer Commit schließt den Vorgang ab; jeder Fehler löst den gemeinsamen Rollback aus.

Die Korrektur referenziert sowohl die Zahlung als auch genau das ursprüngliche Zahlungszuordnungsereignis. Der Korrekturkopf referenziert Quell- und Ziel-OP. Seine beiden Ereignisse sind über `correction_id` und ihre Rolle miteinander verknüpft. Das ursprüngliche Zahlungsereignis und der Zahlungssatz werden nicht geändert.

Die Restberechnung lautet sinngemäß: Ursprungsbetrag abzüglich Zahlungsereignisse, Verrechnungsereignisse und der signierten Korrekturdeltas. Das Entlastungsdelta der Quelle ist negativ und erhöht damit deren offenen Betrag; das positive Zielereignis vermindert den offenen Zielbetrag.

## Ausgeführte Prüfungen

- Fokussierte Korrektur- und OP-Integrationstests einschließlich Zahlungs-, Gutschriften-, Rechnungs- und Verrechnungsregressionen: **50 bestanden** (gemeinsamer Lauf; PostgreSQL-spezifische Migrationsprüfungen ausgeschlossen).
- `tests/database/test_migration_service.py -k 'not postgresql'`: **6 bestanden**.
- Ruff für geänderte Python-Dateien: **bestanden**.
- `git diff --check`: **bestanden**.

Der vollständige Migrationsdienst-Lauf wurde ebenfalls versucht. Darin schlugen acht PostgreSQL-spezifische Tests fehl: mehrere Test-Doubles akzeptieren das derzeit übergebene `connect_args`-Argument nicht; die Tests, die eine echte Verbindung verwenden, konnten den lokalen PostgreSQL-Server in der Laufumgebung nicht erreichen. Diese Ergebnisse belegen daher keine erfolgreiche PostgreSQL-Migrationsprüfung. Es wurde nichts installiert und keine externe Datenbank verändert.

## Einschränkungen

- Die Integrationstests laufen mit SQLite und aktivierten Fremdschlüsseln. Eine PostgreSQL-Integration konnte in dieser Umgebung nicht bestätigt werden.
- Die neue Dialogoberfläche wurde nicht interaktiv mit einem sichtbaren Qt-Desktop geprüft; ihre Module wurden durch Ruff geprüft.
- Es gibt weiterhin keine Workflows zum Storno tatsächlicher Zahlungen, zu Rückzahlungen, Guthaben aus Überzahlungen, Anzahlungen oder automatischer Korrektur.
- Export, Import, Sicherung, Wiederherstellung und Mandantenlöschung wurden entsprechend der Stufenabgrenzung nicht erweitert.

## Arbeitsbaum

Es wurde kein Commit erstellt. Neben den Änderungen dieser Stufe bestehen unabhängige Änderungen an PostgreSQL-Benutzerverwaltung, Benutzerhandbuch, Datenbankkonfiguration und älteren Kontextdokumenten; sie wurden nicht inhaltlich bearbeitet oder bereinigt.
