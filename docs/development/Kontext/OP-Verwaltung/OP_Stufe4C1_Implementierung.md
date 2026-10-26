# SimpleOB – Implementierungsbericht Stufe 4C-1

## Umfang

Die OP-Übersicht ist eine mandantenbezogene, rein lesende Ansicht der aktuellen
OP-Situation. Sie enthält Forderungen, Verbindlichkeiten, Kundenguthaben und
Lieferantenguthaben. Zahlungs-/Zuordnungslogik und bestehende Buchungswege
blieben unverändert; ergänzt wurde die lesbare Textbildung für OP-Zahlungen.

## Implementierte Funktionen

- Auswahl eines Geschäftspartners oder Anzeige aller Geschäftspartner des
  Mandanten.
- Aktuelle OPs mit Auswahl **„Nur offene Posten“** (Voreinstellung),
  **„Nur vollständig ausgeglichene Posten“** oder **„Alle Posten“**.
- Summen nach Geschäftspartner **und OP-Art**. Forderungen, Verbindlichkeiten
  und beide Guthabenarten werden getrennt ausgewiesen und nicht miteinander
  saldiert.
- Einzelposten mit Belegnummer, Beleg- und Buchungsdatum, Fälligkeit, Ursprung,
  Zahlungen netto, Verrechnungen und offenem Rest.
- Lesende Ereignisdetails mit Ursprungsbeleg, Zahlungszuordnungen,
  Verrechnungen und Zahlungszuordnungskorrekturen. Korrekturdetails verweisen
  weiterhin auf die ursprüngliche Zahlung; sie werden nicht als zusätzliche
  Bank- oder Kassenzahlung dargestellt.
- Sichtbarer Hinweis, dass die Ansicht aktuelle Restbeträge und keine
  historische Stichtagsauswertung zeigt.
- Integration als eigener Tab „OP-Übersicht“ im Hauptfenster.
- Neue OP-Zahlungen erhalten bereits beim Erzeugen der Hauptbuchbuchung einen
  aussagekräftigen Buchungstext. Bei einer einzelnen Kunden-Teilzahlung lautet
  das Muster `Teilzahlung [Partner], Rechnung [Nummer]`, bei einer einzelnen
  Lieferanten-Teilzahlung `Teilzahlung an [Partner], Rechnung [Nummer]`.
  Vollzahlungen verwenden `Kundenzahlung [Partner], Rechnung [Nummer]` oder
  `Lieferantenzahlung [Partner], Rechnung [Nummer]`. Sammelzahlungen verwenden
  `Kundenzahlung [Partner], [n] Rechnungen` beziehungsweise
  `Lieferantenzahlung [Partner], [n] Rechnungen`. Ein vom Benutzer eingegebener
  Text bleibt erhalten und wird um diesen Bezug ergänzt. Bestehende Buchungen
  werden nicht verändert.
- Korrekturdialog und OP-Ereignisdetails verwenden fachliche Referenzen statt
  sichtbarer UUIDs. Der Korrekturdialog nennt Richtung, Partner,
  Ursprungsrechnung, Zahlungs- und Buchungsdatum, Zuordnungs- und Gesamtbetrag,
  Korrekturbetrag sowie Erfassungszeit. Die OP-Details nennen Partner,
  Rechnungs-/Gutschriftnummer, Vorgangsart und die vorhandenen Daten und
  Beträge. Bei Zuordnungskorrekturen sind Quell- und Zielrechnung, ursprüngliche
  Zahlung sowie Begründung erkennbar; der Text weist ausdrücklich auf das
  Ausbleiben einer neuen Bank-/Kassenbewegung hin. Interne UUIDs bleiben als
  versteckte Auswahl- und Referenzwerte bestehen.

Die Statusauswahl aktualisiert die Daten unmittelbar. Einzelpostentabelle und
Summen verwenden dieselbe gefilterte Postenmenge. Ein Posten gilt nur dann als
vollständig ausgeglichen, wenn sein aktueller `Decimal`-Restbetrag exakt
`0.00` beträgt. Die vorhandenen Restbetragsberechnungen bleiben unverändert;
für die beiden Ansichten, die ausgeglichene Posten einschließen, werden diese
Posten aus derselben lesenden Übersicht bezogen und in der Qt-Ansicht gefiltert.

## Buchungstexte und lesbare OP-Referenzen

Die Zahlungserfassungsmaske übergibt ihr optionales Textfeld an
`OpenItemPaymentService.post_payment_allocations()`. Der Service reichte den
Wert zuvor unverändert an `Booking.description` weiter; bei leerem Feld wurde
der Text bereits beim Erzeugen der Hauptbuchbuchung leer gelassen. Das Journal
liest und zeigt `Buchung.description` über den bestehenden Speicher- und
Anzeigepfad. Der Fehler entstand damit bei der Buchungserzeugung, nicht in der
Journalanzeige. Neue Zahlungen erhalten jetzt einen Text nach den oben
aufgeführten Mustern. Vorhandene Buchungen bleiben unverändert.

Die Korrekturdatensätze enthalten weiterhin UUIDs als interne Beziehungen.
`CorrectablePaymentAllocation` liefert zusätzlich Partnername, Buchungsdatum,
Zahlungsgesamtbetrag, Buchungsbeleg und Erfassungszeit an den Dialog. Die
Auswahlliste zeigt daraus lesbare und bei Sammelzahlungen durch die
Rechnungsnummer unterscheidbare Angaben. Die Zielauswahl zeigt Rechnungsnummer,
Belegdatum und offenen Betrag.

In den OP-Ereignisdetails wurden sichtbare Zahlungs-, Buchungs-, Ereignis-,
Korrektur- und Verrechnungs-UUIDs entfernt. Zahlungszeilen nennen Richtung,
Partner und Rechnungsnummer; Datum, Buchungsdatum und Zuordnungsbetrag stehen
in den zugehörigen Spalten. Verrechnungszeilen zeigen die verbundene
Gutschrift beziehungsweise Rechnung. Korrekturzeilen nennen die Quell- und
Zielrechnung, die ursprünglichen Zahlungsdaten und die Begründung. Korrekturen
bleiben als Zuordnungskorrekturen gekennzeichnet und weisen darauf hin, dass
keine neue Bank-/Kassenbewegung entsteht.

## Berechnungsgrundlagen

`OpenItemOverviewRepository` lädt die OPs mandantenbezogen und über alle
Geschäftsjahre. Bei Rechnungs-OPs verwendet es
`OpenItemPaymentRepository.get_open_invoice()` als maßgebliche Quelle für den
aktuellen Restbetrag. Damit bleiben vorhandene Zahlungen, Korrekturen und die
Restbetragslogik der OP-Verwaltung führend. Der ausgewiesene Nettobetrag der
Zahlungen wird aus Ursprungsbetrag, den Verrechnungsereignissen und genau
diesem vorhandenen Restbetrag hergeleitet; Korrekturereignisse werden daher
nicht ein zweites Mal als Zahlung abgezogen.

Bei Guthaben-OPs wird `OpenItemOffsetRepository.get_credit()` verwendet.
Verrechnungen werden als Ursprungsbetrag minus aktuell verfügbares Guthaben
ausgewiesen. Geldwerte bleiben `Decimal`-Werte. Alle vier OP-Arten verwenden
dieselben mandantengebundenen Eingangsdaten und werden separat gruppiert.

Detailabfragen werden erst für einen OP ausgeführt, der zuvor über die
mandantenbezogene Übersicht gefunden wurde. Die Auswertung schreibt keine
OP-, Zahlungs-, Buchungs- oder Ereignisdaten. Es wurde keine Migration
benötigt.

## Geänderte und neue Dateien

- `src/simpleob/domain/open_item_overview.py` – unveränderliche Ergebnis- und
  Aktivitätsdatentypen.
- `src/simpleob/database/open_item_overview_repository.py` – mandantenbezogene
  Leseabfragen und Ereignisdetails unter Wiederverwendung der bestehenden
  Restbetrags-Repositories.
- `src/simpleob/services/open_item_overview_service.py` – lesende
  Anwendungsfassade.
- `src/simpleob/ui_qt/open_item_overview_widget.py` – Filter, Summen-,
  Einzelposten- und Ereignistabellen.
- `src/simpleob/services/open_item_payment_service.py` – Bildung eines
  verständlichen Buchungstextes aus Zahlungsrichtung, Partner und
  Rechnungszuordnungen; ausdrückliche Benutzereingaben bleiben enthalten.
- `src/simpleob/domain/payment_allocation_correction.py` und
  `src/simpleob/database/payment_allocation_correction_repository.py` –
  lesende Ergänzung der Korrekturauswahldaten um Partnername, Buchungsbezug,
  Zahlungsbetrag, Beleg und Erfassungszeitpunkt.
- `src/simpleob/ui_qt/payment_allocation_correction_dialog.py` – lesbare,
  unterscheidbare Quell- und Zielauswahl ohne sichtbare UUID.
- `src/simpleob/database/open_item_overview_repository.py` und
  `src/simpleob/ui_qt/open_item_overview_widget.py` – Ereignisreferenzen ohne
  sichtbare Zahlungs-, Buchungs-, Ereignis-, Korrektur- oder
  Verrechnungs-UUID.
- `src/simpleob/ui_qt/main_window.py` – optional injizierter OP-Übersichtstab.
- `src/simpleob/qt_main.py` – Aufbau und Übergabe des Lese-Services.
- `tests/integration/test_open_item_overview.py` – Integration über alle vier
  Arten, Zahlungen, Korrekturen, Verrechnungen, abgeschlossene Vorjahre,
  Mandantentrennung und Schreibfreiheit.
- `tests/ui/test_open_item_overview_widget.py` – alle drei Statusfilter,
  konsistente Summen und Einzelposten, Partnerfilter, Detailanzeige und lesende
  Oberfläche.
- `tests/ui/test_payment_allocation_correction_dialog.py` – lesbare
  Korrekturauswahl für Kunden- und Lieferantenzahlungen ohne sichtbare UUIDs.
- `tests/integration/test_open_item_payment.py` und
  `tests/integration/test_open_item_overview.py` – Buchungstexte für einzelne
  Kunden-/Lieferantenzahlungen, Teilzahlungen und Sammelzahlungen sowie
  lesbare OP-Ereignisreferenzen.

Das Benutzerhandbuch wurde nicht geändert.

## Manueller Praxistest

Der Benutzer hat die relevanten GUI-Funktionen praktisch geprüft: eine Rechnung
mit Teilzahlung und den angezeigten OP-Restbetrag, alle drei Statusfilter,
Buchungstexte neu erfasster Zahlungen sowie die lesbaren Angaben im
Korrekturdialog und in den OP-Ereignisdetails. Die Funktionen wurden dabei als
funktionierend bestätigt. Dies war ein gezielter Praxistest dieser Abläufe und
keine vollständige GUI-Abnahme.

## Prüfungen

- `.venv/bin/python -m pytest -q tests/integration/test_open_item_payment.py tests/integration/test_payment_allocation_correction.py tests/integration/test_open_item_overview.py tests/ui/test_open_item_overview_widget.py tests/ui/test_payment_allocation_correction_dialog.py` – **20 bestanden**.
- Ruff für alle in dieser Ergänzung geänderten Python-Dateien – **bestanden**.
- `git diff --check` – **bestanden**.

## Einschränkungen

- Die Ansicht zeigt ausschließlich aktuelle Restbeträge. Eine historische
  OP-Einzelpostenberechnung zu einem Stichtag ist ausdrücklich nicht enthalten;
  die Sammelkontoabstimmung aus Stufe 4A bleibt unverändert.
- Sammelkontobewegungen ohne OP-Zuordnung, OP-Korrekturen außerhalb der bereits
  vorhandenen Ereignistypen und historische OP-Übernahmen werden nicht ergänzt.
- Ein möglicher Performancebedarf bei sehr großen Mandantenbeständen ist noch
  nicht durch Lastmessungen bewertet.
- Die UI wurde durch den gezielten Qt-Test auf Filterung und Tabellenanzeigen
  geprüft; ein vollständiger manueller GUI-Abnahmelauf wurde nicht
  durchgeführt.

## Abgrenzung

Nicht implementiert wurden Stornierungen, Forderungsverluste, manuelle
Sammelkonto-Zuordnungen, Überzahlungen, Anzahlungen, historische OP-Übernahmen,
Jahresabschlusssperren, § 19 UStG sowie Mandantenexport, -import, Sicherung,
Wiederherstellung oder Löschung. E-Bilanz/ERiC und das Benutzerhandbuch blieben
außerhalb des Umfangs.
