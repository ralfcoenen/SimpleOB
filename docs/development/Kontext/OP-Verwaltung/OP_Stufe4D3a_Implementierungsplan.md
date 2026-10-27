# SimpleOB – Stufe 4D-3a: Implementierungsplan für Rechnungsstornos mit Zahlungen

## 1. Ziel und Geltungsbereich

Dieser Plan übersetzt die verbindlichen Entscheidungen aus [OP_Stufe4D3_Fachkonzept.md](OP_Stufe4D3_Fachkonzept.md) in einen kleinen, überprüfbaren Implementierungsumfang. Er ist keine Implementierungsfreigabe.

4D-3a umfasst teilweise und vollständig bezahlte Ausgangs- und Eingangsrechnungen ohne Gutschriftenverrechnungshistorie. Die Rechnungsgegenbuchung, eine gegebenenfalls erforderliche Umbuchung auf Partnerguthaben und alle OP-Daten werden gemeinsam gespeichert. 4D-3b (Rücknahme von Gutschriftenverrechnungen) bleibt ausdrücklich außerhalb des Umfangs.

## 2. Tatsächlicher Ausgangscode und betroffene Komponenten

### Modell und Transaktion

- `src/simpleob/database/models.py`: `Ausgangsrechnung`, `Eingangsrechnung`, `ForderungsOP`, `VerbindlichkeitsOP`, `RechnungsOPStorno`, `GuthabenOP`, `GuthabenOPEreignis`, Zahlungs- und Korrekturereignisse.
- `migrations/versions/d4a2f19c7b60_add_unpaid_invoice_open_item_stornos.py`: aktuelle 4D-2-Migration; die 4D-3a-Migration muss auf dem beim Implementieren festgestellten aktuellen Alembic-Head aufsetzen.
- `src/simpleob/database/open_item_invoice_cancellation_repository.py`: `preview()`, `add_atomic()`, `_load_eligible_invoice()`, `_ensure_no_history()`. Gegenbuchung wird hier bereits als persistiertes `Buchung`-Modell erstellt, weil `BookingRepository.add()` eine allgemeine OP-Gegenbuchung ausdrücklich sperrt.
- `src/simpleob/services/open_item_invoice_cancellation_service.py`: explizite Bestätigung und Delegation zum Repository.
- `src/simpleob/domain/open_item_invoice_cancellation.py`: `InvoiceCancellationPreview`, derzeit auf unbezahltes Storno ausgerichtet.

### Zahlung und Kontierung

- `src/simpleob/database/open_item_payment_repository.py`: `get_open_invoice()` berechnet aktuellen Restbetrag; dies ist die maßgebliche Basis für `R` und die bestehende Zahlungs-/Verrechnungsvalidierung.
- `src/simpleob/services/open_item_payment_service.py`: `post_payment_allocations()` prüft OPs und Kontenrollen und erzeugt je tatsächlicher Zahlung genau eine Buchung.
- `src/simpleob/database/payment_allocation_correction_repository.py`: `get_correctable()` und Korrekturereignisse mit signierten Deltas; `booking_date` ist separat vorhanden und kann bei Altbestand unbekannt (`NULL`) sein.
- `src/simpleob/services/payment_allocation_correction_service.py`: sperrt Quell- und Ziel-OP über vorhandene Repository-Aufrufe und speichert optionale Kontenumbuchung plus Korrektur atomar.
- `src/simpleob/database/chart_of_accounts_repository.py`: vorhandene mandantenspezifische Kontenrollenvalidierung für Forderungen, Verbindlichkeiten und Guthaben. Diese bleibt einzige Konfigurationsquelle.
- `src/simpleob/database/booking_repository.py`: `add(..., commit=False)` ist für die normale reine Guthabenumbuchung wiederverwendbar; keine Änderung an der allgemeinen Sperre für OP-Ursprungsbuchungen.

### Guthabenverrechnung, Anzeige und Abstimmung

- `src/simpleob/database/open_item_offset_repository.py`: `get_invoice()`, `get_credit()`, `list_open_credits()`, `add()`. Guthaben werden derzeit ausschließlich über `Gutschrift` aufgelöst. Diese drei Lese-/Validierungspfade müssen eine Stornoherkunft zusätzlich verstehen.
- `src/simpleob/services/open_item_offset_service.py`: bestehender Offsetablauf; Fachlogik für neue allgemeine Verrechnungsarten ist nicht vorgesehen. Er soll stornobasierte Guthaben durch dieselbe Auswahl und Verrechnung führen können.
- `src/simpleob/database/open_item_overview_repository.py`: `list_items()`, `_invoice_item()`, `_invoice_activities()`, `_credit_activities()`, `get_detail()`.
- `src/simpleob/domain/open_item_overview.py`, `src/simpleob/services/open_item_overview_service.py`, `src/simpleob/ui_qt/open_item_overview_widget.py`, `src/simpleob/ui_qt/open_item_detail_dialog.py`: Domänenanzeige, lesende Details und aktuelle Stornoaktion.
- `src/simpleob/database/open_item_reconciliation_repository.py`: `reconcile()` muss stornobasierte Guthaben und deren Übertragungsbuchung auf dem tatsächlichen Konto ausweisen sowie beide neuen Buchungen als bekannte OP-Bewegungen einordnen.
- `src/simpleob/qt_main.py` und `src/simpleob/ui_qt/main_window.py`: nur prüfen/anpassen, falls neue Abhängigkeiten für Kontenrollen oder Refresh benötigt werden.

### Tests, die voraussichtlich gezielt anzupassen/zu ergänzen sind

- `tests/integration/test_open_item_overview.py`: bestehende 4D-2-Stornofälle, Übersicht, Abstimmung, Rollback und Konkurrenz.
- Vorhandene Payment-/Offset-Integrationstests (`tests/integration/test_open_item_payment.py`, `test_open_item_offset.py`) für stornierte OP-Guards und stornobasiertes Guthaben.
- `tests/ui/test_open_item_overview_widget.py`: Aktion für bezahlte/ausgeglichene Rechnungen, Vorschau-/Bestätigungstext und Aktualisierung.
- Migration-Tests bzw. bestehende Alembic-Head-/SQLite-Migrationstests für Altbestand-Backfill. PostgreSQL-Integration nur sofern vorhandene Testumgebung verfügbar ist.

## 3. Minimales Datenmodell und Migration

### 3.1 `RechnungsOPStorno`

Bestehender `amount` bleibt voller Rechnungsbetrag `I` und entspricht dem Betrag, dessen Ursprungsbuchung exakt gespiegelt wird. Ergänzt wird:

| Änderung | Regel |
|---|---|
| `closed_open_amount NUMERIC(18,2) NOT NULL` | OP-Restbetrag `R`; Check `0 <= closed_open_amount <= amount` |
| `credit_booking_id VARCHAR(36) NULL` | eindeutiger FK auf `buchungen.booking_id`; Buchung für den Guthabenübertrag, nur bei `P > 0` vorhanden |

Für bestehende 4D-2-Zeilen wird `closed_open_amount = amount` gesetzt. Damit bleiben alle bisherigen unbezahlten Stornos fachlich und rechnerisch identisch. `amount > 0`, Rechnung-/OP-Eindeutigkeit, Storno-Identität und Gegenbuchungsreferenz bleiben erhalten. `credit_booking_id` benötigt einen Unique-Constraint, damit eine Übertragungsbuchung keinem zweiten Storno zugeordnet wird.

Ein Feld für ein zweites OP-Datum ist unnötig: Rechnungs-OP-Schließung wird durch die Stornobuchung `booking_id` zeitlich bestimmt; Guthabenentstehung durch `credit_booking_id` und deren `Buchung.booking_date`.

### 3.2 `GuthabenOP`

`credit_note_id` wird optional, und es kommt `invoice_cancellation_id` als optionale eindeutige FK-Quelle auf `RechnungsOPStorno.storno_id` hinzu. Eine Check-Constraint erzwingt genau eine Quelle:

```text
(credit_note_id IS NOT NULL AND invoice_cancellation_id IS NULL)
OR
(credit_note_id IS NULL AND invoice_cancellation_id IS NOT NULL)
```

Bestehende Zeilen bleiben mit gesetztem `credit_note_id` erhalten. Ein stornobasiertes Guthaben erhält `invoice_cancellation_id`; es wird kein `Gutschrift`-Datensatz erzeugt. Richtung, Partner und Mandant werden aus Rechnungsstorno und Ursprungsrechnung verifiziert. Guthabenbetrag ist der positive wirksam bezahlte Betrag `P`; seine Herkunftsbuchung ist `RechnungsOPStorno.credit_booking_id`.

### 3.3 Vereinbarkeit und Constraints

Der Vorschlag ist mit dem aktuellen Modell vereinbar, sofern die Migration die vorhandenen Gutschrift-Guthaben erhält und nullable FKs sowie `CHECK`-Constraint korrekt abbildet. SQLite benötigt für Änderungen bestehender Constraints/Spalten voraussichtlich Alembic-Batch-Operationen; PostgreSQL kann Constraints nativ ergänzen. SQLAlchemy-Querys und Beziehungen, die `credit_note_id` als immer vorhanden behandeln, müssen danach explizit über die exklusive Quellenart unterscheiden.

Constraints sollten absichern:

- `closed_open_amount >= 0 AND closed_open_amount <= amount`;
- genau eine Rechnungsrichtung im Stornokopf wie bisher;
- je Rechnung und OP maximal ein Storno wie bisher;
- je Guthaben-OP genau eine Quelle;
- `UNIQUE(invoice_cancellation_id)` und `UNIQUE(credit_booking_id)`;
- bekannte Primär-/Fremdschlüssel, positive Guthabenbeträge und gültige Geldbeträge.

Mandant, Partner, Richtung und Bezug zwischen Storno, Rechnung, OP, Guthaben-OP und Buchungszeilen sind teilweise tabellenübergreifend. Gewünschte zusammengesetzte FKs dürfen nur verwendet werden, wenn referenzierte Spalten bereits passende Unique-Constraints besitzen oder mit kleiner, kompatibler Ergänzung versehen werden können. Es darf kein unnötiger Umbau der Rechnungstabellen entstehen. Wo kein passender zusammengesetzter FK besteht, muss der dedizierte Repository-Pfad Mandant/Partner/OP/Buchung vor dem Commit erneut validieren. Betragsgleichheit und exakte Gegenbuchungszeilen sind ebenfalls Service-/Repository-Invarianten, keine einfachen `CHECK`s.

### 3.4 Migration und Altbestand

1. Neue Migration auf aktuellem Head (zum Prüfzeitpunkt 4D-2: `d4a2f19c7b60`) anlegen; vor Implementierung `alembic heads` bestätigen.
2. `closed_open_amount` zunächst nullable ergänzen, historische Stornozeilen mit `amount` befüllen, danach `NOT NULL` und Check setzen.
3. `credit_booking_id` nullable hinzufügen.
4. `GuthabenOP.invoice_cancellation_id` nullable hinzufügen; `credit_note_id` nullable ändern; vorhandene `credit_note_id`-Daten unangetastet lassen.
5. Eindeutigkeits-, Quellen- und Betragconstraints ergänzen.
6. Upgrade/Downgrade auf SQLite testen; PostgreSQL-Upgrade und Constraints nach Möglichkeit gegen die freigegebene Testumgebung prüfen. Downgrade darf nur neue Struktur zurücknehmen; vor Storno erzeugte neue Guthaben wären bei Downgrade nicht verlustfrei abbildbar und müssen daher ausdrücklich als Downgrade-Risiko dokumentiert oder durch eine Vorbedingung geschützt werden.

## 4. Betragsberechnung und Datumsregel

### 4.1 Wirksame Zuordnung `P`

Für genau einen Rechnungs-OP:

```text
P = SUM(RechnungsOPZahlungsereignis.amount für diesen OP)
  + SUM(Zahlungszuordnungskorrekturereignis.amount_delta für diesen OP)
```

`SOURCE_RELEASE`-Deltas sind negativ, `TARGET_APPLY`-Deltas positiv. Eine Sammelzahlung wird nicht als ganzer Headerbetrag auf jede Rechnung gezählt. Nur die betroffene OP-ID wird aggregiert. Das aktuelle Residual aus `OpenItemPaymentRepository.get_open_invoice()` bleibt zentrale Rechnung: Bei 4D-3a ohne Verrechnung `R = I − P`. Es muss gelten `0 <= P <= I`; negativer Rest/inkonsistente Ereignisse brechen ab.

### 4.2 Verbindliche Datumsregel

Für die späteste Datumsgrenze werden die maßgeblichen Buchungsdaten der wirksamen Zahlungszuordnungen sowie **alle** Zahlungszuordnungskorrekturen berücksichtigt, bei denen der Rechnungs-OP als Quelle oder Ziel vorkommt. Für Zahlungen ist `Zahlung.booking_id → Buchung.booking_date` maßgeblich. Für Korrekturen gilt ausschließlich das gespeicherte `Zahlungszuordnungskorrektur.booking_date`, auch wenn bei identischen Sammelkonten keine eigene Hauptbuchumbuchung (`booking_id`) existiert.

Das Stornodatum muss mindestens dem spätesten dieser Buchungsdaten entsprechen und im selben offenen Geschäftsjahr liegen. Ein NULL in einem zugehörigen Korrektur-`booking_date` führt zur Ablehnung des Stornos. `correction_date`, das Ereignisfeld `effective_date` und `recorded_at` sind keine Ersatzwerte. Historische Daten werden weder geschätzt noch automatisch geändert.

Die Migration `c71f4db9e2a6` lässt `booking_date` nullable, übernimmt bei vorhandener Hauptbuchreferenz das Buchungsdatum und erhält NULL bei historischen Korrekturen ohne rekonstruierbares Datum. Diese Fälle bleiben für 4D-3a gesperrt.

## 5. Buchungs- und OP-Vorgang

### 5.1 Erforderliche Buchungen

Es entstehen ein oder zwei Buchungen, je nachdem, ob `P` null ist:

**Buchung 1 – vollständiges Rechnungsstorno:** alle gespeicherten Originalzeilen exakt spiegeln, `BookingType.REVERSAL`, `reversal_of_booking_id` auf die Originalbuchung. Keine Umsatzsteuerneuberechnung.

**Buchung 2 – Guthabenumbuchung, nur wenn `P > 0`:**

| Richtung | Soll | Haben |
|---|---|---|
| Kundenrechnung | tatsächliches Forderungskonto der Ursprungsbuchung `P` | mandantenspezifische Kunden-Guthabenkontenrolle `P` |
| Lieferantenrechnung | mandantenspezifische Lieferanten-Guthabenkontenrolle `P` | tatsächliches Verbindlichkeitskonto der Ursprungsbuchung `P` |

Die Kontenrolle wird über `ChartOfAccountsRepository` validiert, inklusive Mandant und erwartetem Aktiv-/Passivkontotyp. Das tatsächliche Rechnungs-Sammelkonto wird anhand der Originalbuchungszeilen ermittelt. Keine feste Kontonummer. Keine Bank-/Kassenzeile. Die beiden Belege erhalten nachvollziehbare, unterscheidbare Referenzen auf Rechnung und Storno.

### 5.2 Nebenbuchvorgang

- `RechnungsOPStorno.amount = I` dokumentiert den vollen Stornobetrag.
- `RechnungsOPStorno.closed_open_amount = R` dokumentiert den OP-Schließbetrag.
- `RechnungsOPStorno.booking_id` referenziert die Spiegelbuchung.
- Bei `P > 0`: `credit_booking_id` referenziert die Guthabenumbuchung und `GuthabenOP.amount = P`, Herkunft `invoice_cancellation_id`.
- Bei `P = 0`: kein Guthaben-OP, kein `credit_booking_id`.
- Bei `R = 0`: kein künstliches Rechnungs-OP-Ereignis; Stornokopf markiert und sperrt den bereits ausgeglichenen OP.

Das Zahlungsmittel und der Zahlungskopf bleiben unverändert. Der neue Guthaben-OP beschreibt den nach Storno aus der realen Zahlung resultierenden Partneranspruch, nicht eine neue Zahlung.

## 6. Autorisierung, Transaktion und Schutz

1. `preview()` validiert Mandant, Partnerrolle, Ursprungs-OP, Originalbuchung, gleiche offene Geschäftsjahre und lesbare Zahlungshistorie; es liefert `I`, `P`, `R`, wirksame Datumsgrenze sowie beide geplanten Buchungssätze. Vorschau ist keine Schreibautorisierung.
2. `cancel_invoice()` verlangt weiterhin `confirmed=True` sowie verpflichtenden Grund und ruft nur den dedizierten atomaren OP-Stornoweg auf.
3. `add_atomic()` öffnet keine separate Session und committet nicht vorzeitig. Es prüft alle Voraussetzungen unter Sperre erneut.
4. PostgreSQL: OP-Zeile und Geschäftsjahr mit `FOR UPDATE`; relevante Zahlungsereignisse/Korrekturköpfe konsistent erneut lesen. Zahlung und Korrektur müssen ebenfalls denselben OP-Sperrpunkt verwenden, dann nach dem Lock erneut auf Storno prüfen.
5. SQLite: keine wirksame Zeilen-`FOR UPDATE`-Garantie; alles in einer Schreibtransaktion, Unique-Constraints als letzte Sicherung, jede Lock-/Constraint-Kollision rollt sämtliche Buchungen und Nebenbuchdaten zurück.
6. Zuerst oder innerhalb derselben Transaktion Spiegelbuchung dediziert speichern; Guthabenumbuchung über `BookingRepository.add(..., commit=False)` in dieselbe Session einfügen; Stornokopf und Guthaben-OP speichern; flush und genau ein Commit.
7. Die normale `BookingRepository.add()`-Sperre für eine Umkehrung von OP-Ursprungsbuchungen wird nicht gelockert. Keine Freigabe durch frei wählbaren Parameter, Buchungstext, Kontonummer oder UI.

Zu sperrende Folgepfade:

- Zahlung: `OpenItemPaymentService.post_payment_allocations()` / `OpenItemPaymentRepository.get_open_invoice()`.
- Verrechnung: `OpenItemOffsetService.post_offset()` / `OpenItemOffsetRepository.get_invoice()`.
- Korrektur: `PaymentAllocationCorrectionService.correct()` für sowohl Quell- als auch Ziel-OP; Prüfung unter gemeinsamen OP-Sperren.
- Storno: Unique pro Rechnungs-OP/Rechnung und `reversal_of_booking_id`-Duplikatprüfung.

Ein Restbetrag null allein kennzeichnet nicht zuverlässig ein Storno, weil eine gewöhnlich vollständig bezahlte Rechnung ebenfalls null ist. Expliziter Stornostatus muss aus vorhandenem Stornokopf abgeleitet werden.

## 7. Übersicht, Verrechnung und Stichtagsabstimmung

### OP-Übersicht und Details

`OpenItemOverviewRepository.list_items()` muss stornobasierte Guthaben unabhängig von einem `Gutschrift`-Join laden. Geschäftspartner/Richtung/Belegnummer stammen aus Stornokopf und Ursprungsrechnung. Detailaktivitäten zeigen tatsächliche Zahlung, Korrekturen, Rechnungsgegenbuchung und Guthabenumbuchung getrennt; keine UUID als einzige Referenz und keine zweite Bankzahlung.

`OpenItemOverviewWidget._can_cancel_selected_invoice()` prüft derzeit `open_amount > 0`; dies verhindert Storno vollständig bezahlter Rechnungen. Die Zulässigkeit muss für Rechnungsarten stattdessen an Auswahl und vorhandenen Service gebunden sein, die Details zum konkreten Ausschluss liefert der Preview-Service. Vollständig bezahlte OPs sind über den ausgeglichenen/alle-Filter erreichbar. Vorschau zeigt `I`, `P`, `R`, Guthabenbetrag und die Buchungszeilen beider Buchungen; ausdrücklich bestätigen.

### Bestehende Guthabenverrechnung

`OpenItemOffsetRepository.get_credit()` ermittelt Quelle, Partner, Richtung, Restbetrag und reales Gegenkonto aus Gutschriftbuchung. Bei Stornoherkunft muss dieselbe fachliche Zusammenfassung aus Ursprungsrechnung und `credit_booking_id` gewonnen werden. `list_open_credits()` muss beide Herkunftsarten aufführen. `post_offset()` kann dieselbe Kontierung und Ereigniserzeugung verwenden, sofern es Guthabenquelle über einheitliche Summary auflöst und die Kontierung das im Guthabenübertrag tatsächlich bebuchte Konto nutzt. Keine neue Verrechnungsart und keine Geldbewegung.

### Abstimmung

`OpenItemReconciliationRepository.reconcile()`:

- berücksichtigt die Rechnungs-OP-Schließung `R` erst ab `RechnungsOPStorno.booking_id.booking_date`;
- erkennt Spiegelbuchung und Guthabenumbuchung als OP-gebundene Hauptbuchbewegungen;
- fügt den stornoabgeleiteten Guthaben-OP seinem tatsächlichen Forderungs-/Verbindlichkeits-Guthabenkonto erst ab `credit_booking_id.booking_date` zu;
- erhält historische Salden vor den jeweiligen Buchungsdaten;
- wertet spätere Guthabenverrechnung als Ereignis des Guthaben-OP aus und zieht sie ab deren Buchungsdatum ab.

Wenn `P = 0`, darf keine Guthabenbewegung erwartet werden. Alle Beträge und Vorzeichen folgen den vier schon implementierten Kontenrollen; es werden keine Konten erfunden.

## 8. Technische Risiken vor der ersten Änderung

1. **Unbekanntes historisches Korrekturbuchungsdatum:** bestehende `NULL`-Werte verhindern eine exakte Prüfung des spätesten Datums. Verbindliche Regel: betroffenes Storno ablehnen; kein Ersatzdatum verwenden.
2. **Schreibkonkurrenz über Zahlungs-/Korrekturpfade:** Stornodienst, Zahlung, Verrechnung und Korrektur müssen dieselben OP-Zeilensperren in konsistenter Reihenfolge verwenden. Sonst kann eine nach der Prüfung konkurrierend eingetragene Zuordnung OP und Hauptbuch entkoppeln.
3. **Unique-/FK-Kompatibilität:** Optionale exklusive Guthabenquelle muss unter SQLite und PostgreSQL gleich funktionieren. Nullable `UNIQUE` ist für beide vorgesehen, aber Migrations- und Constraintverhalten ist konkret zu validieren.
4. **Guthaben-OP-Verbrauch:** Nach Stornierung des Ursprungs-OP muss der Guthaben-OP in bestehende Offsetabfragen passen, ohne vorhandene Gutschriften-Datensätze zu fingieren.
5. **Stichtagskonsistenz:** zwei Buchungen haben je ein Hauptbuchdatum. Stornoabschluss und Guthabenentstehung müssen nach den jeweils eigenen Daten berechnet werden. Für 4D-3a wird dasselbe eingegebene Datum vorgeschlagen, damit beides gemeinsam wirksam wird; unterschiedliche Daten sind nicht Bestandteil dieser Stufe.
6. **Migrations-Downgrade:** Nach Anlage stornobasierter Guthaben ist ein Downgrade in das alte Schema nicht verlustfrei möglich. Das ist für den üblichen Upgradeweg unproblematisch, muss aber in Downgrade-Strategie dokumentiert werden.

## 9. Kleinschrittiger Implementierungs- und Testplan

### Schritt 1 – Datenstruktur

Modelle plus eine additive Alembic-Migration. Backfill `closed_open_amount = amount`; vorhandene Gutschrift-Guthaben bleiben unverändert. Gezielte Migrationstests prüfen Upgrade, Constraints, vorhandene Zeilen und PostgreSQL/SQLite-Unterstützung soweit verfügbar.

### Schritt 2 – Preview und zentrale Betragsermittlung

`InvoiceCancellationPreview` liefert Zahlungssumme `P`, Rest `R`, max. wirksames Buchungsdatum, Guthabenkonto und beide geplanten Buchungssätze. Integrationstests decken eine Zahlung, mehrere Zahlungen, Sammelzahlung mit Zuordnungen und Korrekturanteile ab. Fälle mit Verrechnungshistorie bleiben abgewiesen.

### Schritt 3 – Atomare Stornobuchung

Erweitere den bestehenden spezialisierten Repositorypfad: exakte Spiegelung, optionaler reiner Übertrag `P`, Stornokopf, Storno-Guthaben-OP und Rechnungsrest `R` gemeinsam committen. Tests für Kunden/Lieferanten, vollständig/teilweise bezahlt, `P=0`, kein Nullereignis, Kontenrichtung/Betragsgleichheit, keine Bankzeile, Doppelstorno und Rollback.

### Schritt 4 – Konsistenz-Guards und Konkurrenz

Nachzahlungen, Offsets und Korrekturen gegen stornierte Rechnungen ablehnen. Mandant, Partner, Jahr, Datum und keine Verrechnungshistorie prüfen. Separate Session-Konkurrenztests für Doppelstorno sowie Rennen Zahlung/Korrektur gegen Storno; erwartetes Ergebnis genau ein kohärenter Commit und keine Teilbuchung.

### Schritt 5 – Guthabenverbrauch, Übersicht und Abstimmung

Stornobasierte Guthaben in Offsetliste/Verrechnung nutzbar machen. Overview, Detail und Reconciliation anpassen. Tests für Verrechnung des neuen Guthabens, verständliche Herkunft, keine doppelte Zahlung und Stichtage vor/am/nach Storno.

### Schritt 6 – UI und gezielte Regression

Stornoaktion für ausgewählte ausgeglichene Rechnungen verfügbar machen; Preview mit den zwei Buchungssätzen, `I`, `P`, `R` und Guthaben; ausdrückliche Bestätigung bleibt. Gezielte UI-Tests für teilweise/voll bezahlt, keine Auswahl, abgewiesene Verrechnungshistorie und Refresh. Abschließend fokussierte OP-Regression, Ruff und `git diff --check`.

## 10. Ausschlüsse

Nicht in 4D-3a: Storno von Rechnungen mit Verrechnungshistorie; Aufhebung einer Gutschriftenverrechnung; Rückzahlung/Auszahlung; Gutschriftenstorno; Geschäftsjahreswechsel; Forderungsabschreibung; automatische Partnerzuordnung; neue allgemeine OP-Funktionen; E-Bilanz-/ERiC-Änderung; Export/Import/Sicherung/Löschung.

4D-3b wird separat geplant und implementiert. Es nutzt unveränderliche, je Originalverrechnung eindeutig verknüpfte Gegenereignisse/Gegenbuchungen und macht das ursprüngliche Guthaben wieder verfügbar.

## 11. Empfehlung für die erste Implementierungsetappe

Schritt 1 kann separat klein beginnen: ausschließlich Modell-/Migrationsänderung mit verlustfreiem Backfill und Constraints. Für historische `booking_date IS NULL`-Korrekturen gilt die festgelegte Sperrregel. Erst nach erfolgreicher SQLite- und verfügbarer PostgreSQL-Migrationsprüfung folgt die zentrale `P`-/`R`-Vorschau.
