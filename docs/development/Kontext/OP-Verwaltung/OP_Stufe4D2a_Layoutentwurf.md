# Stufe 4D-2a – Bestandsaufnahme und Entwurf der OP-Übersicht

## 1. Bestandsaufnahme der tatsächlichen Oberfläche

### Aufbau und Platzbedarf

`OpenItemOverviewWidget` in `src/simpleob/ui_qt/open_item_overview_widget.py` verwendet ein einziges `QVBoxLayout`. Von oben nach unten enthält es:

1. den Hinweis „Aktuelle OP-Situation – keine historische Stichtagsauswertung.“;
2. eine horizontale Filterzeile mit Geschäftspartner, Postenstatus und „Aktualisieren“;
3. Überschrift und Summen-Tabelle mit sieben Spalten;
4. Überschrift und Einzelposten-Tabelle mit zehn Spalten;
5. optional die Schaltfläche „Rechnung vollständig stornieren“;
6. Überschrift und Ereignistabelle mit sechs Spalten.

Alle drei Tabellen liegen gleichzeitig im Layout. Die Tabellen passen ihre Spalten teilweise an den Inhalt an; die Einzelpostentabelle hat für die Belegnummer eine Stretch-Spalte. Im Widget ist kein Scrollbereich, keine einklappbare Detailgruppe und keine feste kompakte Höhenaufteilung definiert. Das ist die naheliegende strukturelle Erklärung für den hohen Platzbedarf: Die Ereigniszeilen beanspruchen auch dann Höhe, wenn gerade eine andere Aufgabe im Vordergrund steht. Aus dem Code allein lässt sich nicht beweisen, auf welchen Bildschirmgrößen ein konkretes Element tatsächlich abgeschnitten wird.

### Filter, Auswahl und Aktualisierung

- Der Geschäftspartnerfilter zeigt „Alle Geschäftspartner“ und danach sämtliche Partner aus dem Bericht. Er wird beim Ändern unmittelbar neu gerendert.
- Der Statusfilter bietet „Nur offene Posten“, „Nur vollständig ausgeglichene Posten“ und „Alle Posten“. Er ruft beim Wechsel `refresh()` auf; die Einzelposten und Summen werden mit derselben gefilterten Menge neu aufgebaut.
- „Aktualisieren“ lädt den Bericht erneut.
- Eine Auswahl in der Einzelpostentabelle lädt über `get_detail()` die Ereignisse für den aktuellen OP in die darunterliegende Ereignistabelle.
- Nach dem Rendern wird die erste verfügbare Tabellenzeile ausgewählt und deren Detail sofort angezeigt.

Eine Geschäftspartnerart-Auswahl (Kunden/Lieferanten) ist nicht vorhanden. Die Art der OPs ist bereits im `OpenItemKind` abgebildet: Kundenforderung, Lieferantenverbindlichkeit, Kundenguthaben und Lieferantenguthaben.

### Vorhandene Aktionen

- **Rechnungsstorno:** Die Schaltfläche wird in `OpenItemOverviewWidget` nur erstellt, wenn ein `OpenItemInvoiceCancellationService` übergeben wurde. Sie wird für offene Kundenforderungen und Lieferantenverbindlichkeiten aktiviert. Der Klick prüft zunächst die Stornierbarkeit über `preview()`, fragt Buchungsdatum und Grund ab und verlangt eine ausdrückliche Ja/Nein-Bestätigung. Guthaben-OPs und ausgeglichene Rechnungen können über diese Schaltfläche nicht storniert werden.
- **Zahlung:** `MainWindow._open_payment_dialog()` öffnet `OpenItemPaymentDialog` über eine Schaltfläche im Reiter „Buchen“. Das Dialogmodell unterstützt Kundenzahlungen, Lieferantenzahlungen und ausdrückliche Zuordnungen.
- **Gutschriftenverrechnung:** `MainWindow._open_offset_dialog()` öffnet `OpenItemOffsetDialog`, ebenfalls über „Buchen“.
- **Korrektur einer Zahlungszuordnung:** `MainWindow._open_payment_correction_dialog()` öffnet `PaymentAllocationCorrectionDialog` im Reiter „Buchen“.
- Rechnungs- und Gutschriftserfassung erfolgen über die vorhandenen Buchungsabläufe im Reiter „Buchen“.

Die Zahlung, Verrechnung und Zuordnungskorrektur sind derzeit nicht an eine Auswahl in der OP-Übersicht gebunden. Es gibt dort kein Kontextmenü und keine Doppelklick-Verbindung. Die genannten Vorgangsdialoge bleiben eigenständige Abläufe. Das allgemeine Journal-Storno ist eine separate Journalaktion und für OP-Ursprungsbuchungen geschützt.

### Serviceverbindungen und Daten

`src/simpleob/qt_main.py` erstellt `OpenItemOverviewService`, `OpenItemInvoiceCancellationService`, Zahlungs-, Verrechnungs- und Korrekturservices. `MainWindow` erhält diese Services im Konstruktor. In `src/simpleob/ui_qt/main_window.py` wird das Widget einmal im Tab „OP-Übersicht“ erzeugt und mit Mandant, Übersichtsdienst, Stornoservice, Geschäftsjahr und Aktualisierungs-Callback verbunden. Der Callback lädt nach einem Storno Hauptbuchanzeigen neu.

`OpenItemOverviewService` ist eine lesende Weiterleitung an `OpenItemOverviewRepository`. Das Repository fragt mandantenbezogen Rechnungs- und Guthaben-OPs ab und benutzt `OpenItemPaymentRepository` sowie `OpenItemOffsetRepository` für vorhandene Restbetragsberechnungen. Der Report umfasst alle vier OP-Arten. `get_detail()` ergänzt Ereignisse zu Ursprungsbeleg, Zahlung, Verrechnung, Zahlungszuordnungskorrektur und Rechnungsstorno und ordnet sie zeitlich.

Für die Partnerauswahl liefert das Repository derzeit Partner-ID und Name. Das Partnerdomänenmodell kennt `is_customer` und `is_supplier`; ein Partner kann beide Rollen besitzen. OPs selbst liefern ihre Richtung bereits über `OpenItemKind`.

### Vorhandene Tests

`tests/ui/test_open_item_overview_widget.py` enthält derzeit zwei fokussierte GUI-Tests:

- `test_widget_filters_partner_and_settled_items_and_shows_read_only_details` prüft Partner- und Statusfilter, Summen, Ereignisdetails und lesbare Referenzen.
- `test_widget_exposes_explicit_invoice_cancellation_confirmation` prüft die Stornoaktion einschließlich Vorschau, Datums-/Grundabfrage und ausdrücklicher Bestätigung.

Die Daten- und Ereignisfälle werden zusätzlich durch Integrationstests wie `tests/integration/test_open_item_overview.py` abgedeckt. Eine interaktive vollständige GUI-Abnahme ist durch diese Quellprüfung nicht belegt.

## 2. Gegenüberstellung der Layoutvarianten

| Kriterium | Variante A: kompakte Übersicht mit integriertem Detailbereich | Variante B: kompakte Übersicht mit OP-Detaildialog |
|---|---|---|
| Platzbedarf | Niedrig, wenn der Detailbereich standardmäßig eingeklappt ist; bei geöffneten Ereignissen weiterhin zusätzlicher Platzbedarf im Tab | Niedrig und unabhängig von der Fensterhöhe des Hauptfensters; Details erhalten ein eigenes, größenverstellbares Fenster |
| Bedienbarkeit | Auswahl und Details sind gleichzeitig sichtbar; gut für schnelle Sichtprüfung. Ein-/Ausklappen muss klar und auffindbar sein | Hauptliste bleibt ruhig und kompakt; Doppelklick öffnet Details. Wechsel zwischen vielen OPs erfordert Dialog schließen/neu öffnen oder Navigation im Dialog |
| Erweiterbarkeit | Weitere Detailbereiche können den Tab erneut verbreitern oder verlängern; bei guter Trennung prinzipiell möglich | Ereignisse, Zahlungsreferenzen und spätere OP-Aktionen lassen sich im Detailfenster in Tabs/Abschnitte einordnen, ohne die Hauptliste zu belasten |
| Implementierungsaufwand | Eher klein bis mittel: vorhandene Ereignistabelle in eine ein-/ausblendbare Gruppe verschieben und Auswahlverhalten ergänzen | Mittel: neuer Dialog, Übergabe des ausgewählten OPs, Laden/Aktualisieren der Details und zusätzliche Tests |
| Zusätzliche Vorgangsdialoge | Bearbeitungsdialoge müssen weiterhin separat geöffnet werden | Klare Dialoghierarchie: Übersicht → lesender OP-Detaildialog → eigener fachlicher Vorgangsdialog mit Prüfung und Bestätigung |

## 3. Empfehlung

Empfohlen wird **Variante B**. Sie adressiert den gegenwärtigen Platzbedarf dauerhaft und trennt die drei Aufgaben klar:

1. Die OP-Übersicht dient der Suche, Filterung und Summen-/Restbetragsübersicht.
2. Der OP-Detaildialog zeigt einen ausgewählten Rechnungs- oder Gutschriften-OP und dessen Ereignishistorie.
3. Ein eigener Vorgangsdialog führt eine konkrete fachliche Bearbeitung aus und zeigt deren Eingaben, Auswirkungen und erforderliche Bestätigung.

Der Detaildialog bleibt lesend. Das Öffnen der Details löst keine Buchung aus. Die konkrete Bearbeitung wird weiterhin nur über eine passende, eindeutig bezeichnete Aktion gestartet; kritische Buchungsvorgänge behalten ihre explizite Bestätigung. Die bestehende Service- und Buchungslogik soll dabei unverändert bleiben.

Variante A wäre eine gute kleinere Zwischenlösung, wenn der Implementierungsaufwand Vorrang hat. Sie beseitigt die Konkurrenz zwischen Ereignistabelle und Übersicht jedoch nur, solange der Detailbereich eingeklappt bleibt; zusätzliche Stufenfunktionen würden den verfügbaren Raum erneut beanspruchen.

## 4. Konkrete Aufteilung der Widgets und Dialoge

### OP-Übersicht im Hauptfenster

`OpenItemOverviewWidget` bleibt im vorhandenen Tab „OP-Übersicht“ in `MainWindow`. Es enthält:

- den sichtbaren Hinweis, dass aktuelle Restbeträge und keine historische Stichtagsauswertung angezeigt werden;
- die beiden unabhängigen Filter;
- eine kompakte Umschaltung zwischen **Einzelposten** und **Summen** (zum Beispiel zwei interne Ansichts-Tabs oder ein primärer Einzelpostenbereich mit kompakter Summenansicht), damit bestehende Summen je Partner und OP-Art erhalten bleiben;
- eine Einzelpostentabelle mit Partner, OP-Art, Belegnummer/-datum, Fälligkeit und offenem Betrag. Breitere Betragsdetails können im Detaildialog erscheinen; die für die aktuelle Restbetragsprüfung wichtige Offen-Spalte bleibt sichtbar;
- eine sichtbare Aktionsleiste für die auf den ausgewählten Posten anwendbaren Aktionen.

Die Übersicht bleibt mandantenbezogen und verwendet unverändert die vorhandenen Overview-Service-Ergebnisse. Der gewünschte Platzgewinn kommt vor allem dadurch zustande, dass die aktuelle Ereignistabelle nicht dauerhaft unter den beiden Übersichtstabellen angezeigt wird.

### OP-Detaildialog

Ein neues `OpenItemDetailDialog` (Dateivorschlag `src/simpleob/ui_qt/open_item_detail_dialog.py`) erhält den bereits ausgewählten `OpenItemOverviewItem` und lädt die Details über `OpenItemOverviewService.get_detail()`. Er zeigt:

- Partner, OP-Art, Belegnummer, Belegdatum, Buchungsdatum und gegebenenfalls Fälligkeit;
- Ursprungsbetrag, Zahlungen, Verrechnungen und aktuellen Restbetrag;
- die vorhandenen Ereignisse in zeitlicher Reihenfolge mit Vorgangs- und Buchungsdatum, Betrag, fachlicher Referenz und Beschreibung;
- Zahlungen als Ereignisse mit Verweis auf den tatsächlichen Zahlungsvorgang. Eine Korrektur der Zuordnung bleibt klar als Korrektur erkennbar und erscheint nicht als zweite Bankzahlung;
- ein Rechnungsstorno als eigenes Ereignis, sofern vorhanden.

Der Dialog soll mit einer angemessenen Startgröße (beispielsweise ca. 900 × 600 logische Pixel), Mindestgröße und anpassbaren Tabellen-/Spaltenbreiten geöffnet werden. Die Größe ist ein Entwurfswert, der auf unterstützten Plattformen praktisch zu prüfen ist.

### Vorgangsdialoge

Zahlungs-, Verrechnungs- und Zahlungszuordnungskorrekturdialoge bleiben eigenständige Dialoge mit ihren bestehenden Services. Das Rechnungsstorno erhält ebenfalls einen klar erkennbaren Vorgangsablauf mit Vorschau, Grund und ausdrücklicher Bestätigung. Ein OP-Detaildialog kann diese Vorgänge später aus einer Aktionenleiste starten, muss dafür aber den ausgewählten Kontext gezielt übergeben und weiterhin die jeweilige Servicevalidierung ausführen.

Im Entwurf werden keine neuen Bearbeitungsfunktionen vorgezogen. Nicht unterstützte Vorgänge werden weder angeboten noch durch generische Aktionen suggeriert.

## 5. Filter- und Bedienkonzept

### Unabhängig kombinierbare Filter

**Geschäftspartnerart:** Alle / Kunden / Lieferanten.

**OP-Status:** Nur offene / Nur ausgeglichene / Alle Posten.

Die Filter wirken gemeinsam auf Einzelposten und Summen. „Offen“ verwendet den bestehenden berechneten `open_amount > 0`; „ausgeglichen“ verwendet exakt `open_amount == 0.00`. Die vier `OpenItemKind`-Werte werden wie folgt gruppiert:

- Kunden: Kundenforderungen und Kundenguthaben.
- Lieferanten: Lieferantenverbindlichkeiten und Lieferantenguthaben.

Ein Geschäftspartner mit beiden Rollen kann daher Posten in beiden Arten anzeigen; der Rollenfilter grenzt die Art der Posten ein, nicht den Partnerdatensatz dauerhaft auf eine einzige Rolle.

Repository-seitig ist keine zusätzliche OP-Art-Abfrage erforderlich: `OpenItemOverviewRepository.list_items()` liefert bereits alle vier OP-Arten; es unterstützt derzeit nur `include_settled`, keinen Geschäftspartnerartfilter. Eine kleine Filterung im Overview-Service oder in der Widget-Präsentationsschicht reicht aus. Für gleichbleibende Summen und Tabellen muss ein einziger gefilterter Item-Satz verwendet werden. Der Statusfilter benötigt weiter die vorhandenen geladenen Ausgleichsdaten; bei „Nur ausgeglichene“ wird wie bisher mit `include_settled=True` geladen und nach aktuellem Restbetrag gefiltert. Die Geschäftspartnerauswahl soll auf Partner beschränkt werden, die nach beiden aktiven Filtern noch OPs haben; nach einer Filteränderung ist eine nicht mehr passende Partnerauswahl zurückzusetzen.

### Navigation und Aktionen

- **Doppelklick auf einen Einzelposten:** öffnet den lesenden OP-Detaildialog.
- **Enter/Leertaste oder zugängliche Schaltfläche „Details“:** öffnet denselben Dialog ohne Rechtsklick.
- **Kontextmenü auf einer Zeile:** zeigt nur zulässige Aktionen für OP-Art und Status. Es dupliziert keine Fachlogik; jede Aktion ruft vorhandene Service-/Dialogpfade auf.
- **Sichtbare Aktionsleiste:** bietet mindestens „Details“ und die für die Auswahl freigegebenen Vorgänge. Damit bleibt die Bedienung ohne Kontextmenü möglich.
- Kontextmenü und Aktionsleiste müssen dieselbe Zulässigkeitslogik nutzen. Der Service prüft die fachliche Zulässigkeit weiterhin endgültig beim Ausführen.

Für die derzeit vorhandenen Aktionen gelten als Vorschlag:

- Zahlung nur für offene Kundenforderungen bzw. Lieferantenverbindlichkeiten;
- Gutschriftenverrechnung nur, wenn ein passender Rechnungs- und Guthaben-OP desselben Partners und derselben Seite ausgewählt beziehungsweise im bestehenden Verrechnungsdialog festgelegt ist;
- Zahlungszuordnungskorrektur nur über deren bestehenden Dialog und nur, wenn korrigierbare Zuordnungen vorhanden sind;
- Rechnungsstorno nur für Rechnungs-OPs, wobei `preview()` die tatsächliche Stornierbarkeit prüft und den konkreten Ausschlussgrund liefert;
- Gutschriften bleiben von der Rechnungsstornoaktion ausgeschlossen.

Die Verfügbarkeit einer Aktion wird nicht allein aus einem UI-Status abgeleitet; die Serviceprüfung bleibt maßgeblich. Buchungs- und Stornovorgänge zeigen vor der Speicherung eine verständliche Vorschau und verlangen eine ausdrückliche Bestätigung, soweit der bestehende Fachablauf dies vorsieht.

## 6. Betroffene Dateien

### Voraussichtlich anzupassen

- `src/simpleob/ui_qt/open_item_overview_widget.py` – kompaktes Hauptlayout, kombinierte Filter, Doppelklick/Aktionen, Öffnen der Detailansicht.
- `src/simpleob/ui_qt/main_window.py` – falls Services oder Aktualisierungs-Callbacks an Detail-/Vorgangsdialoge weitergereicht werden müssen; keine Änderung der Buchungsservices.
- `tests/ui/test_open_item_overview_widget.py` – Filterkombination, Aktionsverfügbarkeit und Details-Navigation.

### Voraussichtlich neu

- `src/simpleob/ui_qt/open_item_detail_dialog.py` – rein lesende OP-Detailansicht und Ereignishistorie.
- `tests/ui/test_open_item_detail_dialog.py` – Anzeige von Ursprungsbeleg, Ereignisarten, verständlichen Referenzen und Größen-/Interaktionsverhalten.

### Nur bei nachgewiesenem Bedarf

- `src/simpleob/services/open_item_overview_service.py` – nur falls die Filterung bewusst in den lesenden Service statt in der Präsentationsschicht liegen soll.
- `src/simpleob/domain/open_item_overview.py` – nur falls Detailansicht eine dort noch nicht enthaltene fachliche Anzeigeinformation benötigt.
- `src/simpleob/database/open_item_overview_repository.py` – für den beschriebenen Rollenfilter voraussichtlich nicht erforderlich; das Repository liefert die vier OP-Arten bereits. Eine Erweiterung wäre nur nach Messung/Begründung für effizientere Datenbankfilterung nötig.

Keine Datenbankmigration ist für das beschriebene Layout- und Filterkonzept erkennbar erforderlich.

## 7. Überschaubarer Implementierungs- und Testplan

1. **Gefilterte Datenmenge vereinheitlichen:** Rollen- und Statusfilter bilden einen gemeinsamen gefilterten Satz; daraus werden Einzelposten und Summen gerendert. Tests prüfen alle neun Filterkombinationen sowie Partner mit beiden Rollen und alle vier OP-Arten.
2. **Hauptübersicht kompakt strukturieren:** Summen und Einzelposten als klar getrennte Ansichten innerhalb der OP-Seite anbieten; Details aus dem dauerhaft sichtbaren Vertikallayout entfernen. GUI-Test prüft die drei Filterzustände und dass Summen-/Einzelpostenansicht dieselbe Filterauswahl verwenden.
3. **Lesenden Detaildialog ergänzen:** Auswahlübergabe und Ereignisanzeige umsetzen. Tests prüfen Ursprungsbeleg, Zahlungen, Verrechnungen, Korrekturen, Storno, sichtbare Buchungs-/Vorgangsdatumswerte und keine Schreibaufrufe.
4. **Navigation und Aktionen anbinden:** Doppelklick, Tastatur/Details-Schaltfläche, Kontextmenü und sichtbare Aktionsleiste auf gemeinsame UI-Zulässigkeitsregeln führen. Tests prüfen mindestens einen Kontextmenü- und einen rechtsklickfreien Weg sowie Status-/OP-Art-Beschränkungen. Vorhandene Buchungsservices und ihre Integrationstests bleiben unverändert.
5. **Geometrie und manuelle Bedienbarkeit prüfen:** Größenanpassung bei typischen Fenstergrößen und hoher Skalierung prüfen; manuell bestätigen, dass Tabelle, Status und Aktionen erreichbar bleiben und der Detaildialog hinreichend Platz für die Ereignisliste hat.

Die Schritte ändern weder Buchungs- und Zahlungslogik noch Restbetragsberechnungen, Abstimmung, Datenbankmodell, Migrationen oder E-Bilanz/ERiC. Stufe 4D-3 wird nicht vorgezogen.

## 8. Offene Gestaltungsentscheidung

Vor der Umsetzung ist insbesondere festzulegen, ob die zusammenfassenden Partner-/OP-Art-Summen als interne zweite Ansicht (empfohlen, um den Hauptbereich kompakt zu halten) oder als stets sichtbare kleine Summenzeile dargestellt werden sollen. Für den Detaildialog ist außerdem zu entscheiden, ob ein Dialog pro OP modal geöffnet wird oder als nichtmodales Fenster bestehen bleiben darf. Fachlich sind beide Varianten lesend; modal ist einfacher gegen veraltete Auswahl zu schützen, nichtmodal erleichtert den Vergleich mehrerer OPs.
