# Stufe 4D-3a, Etappe 3B – OP-Übersicht und Stichtagsabstimmung

## Umsetzung

Die aktuelle OP-Übersicht und die stichtagsbezogene Sammelkontoabstimmung berücksichtigen jetzt bezahlte Rechnungsstornos und Guthaben-OPs aus Rechnungsstornos. Es wurde keine Buchungslogik geändert.

### OP-Übersicht

In `src/simpleob/database/open_item_overview_repository.py` werden Rechnungs-OPs weiterhin über `OpenItemPaymentRepository.get_open_invoice()` berechnet. Die ausgewiesenen Zahlungen werden aus ursprünglichem Betrag, Verrechnungen, `RechnungsOPStorno.closed_open_amount` und aktuellem Restbetrag abgeleitet. Dadurch bleibt bei einem Beispiel mit 1.190 € Ursprungsbetrag, 400 € Zahlung und 790 € Schließbetrag der Zahlbetrag 400 €.

Guthaben-OPs mit `invoice_cancellation_id` werden zusätzlich zu Gutschrift-Guthaben geladen. Mandant, Partner und Guthabenherkunft werden über die bestehende `OpenItemOffsetRepository.get_credit()`-Prüfung validiert. Die Anzeige verwendet die Bezeichnung „Storno [Rechnungsnummer]“, das Buchungsdatum der Guthabenumbuchung und die bestehenden Verrechnungsereignisse. In den Details wird die Herkunft als Rechnungsstorno ausgewiesen.

Das OP-Stornoereignis der Rechnung zeigt `-closed_open_amount`; der Hauptbuchgegenbuchungsbetrag bleibt weiterhin der vollständige Rechnungsbetrag. So entspricht die Detailhistorie der tatsächlichen OP-Schließung und erzeugt kein künstliches Nullbetragsereignis bei vollständig bezahlten Rechnungen.

### Stichtagsabstimmung

In `src/simpleob/database/open_item_reconciliation_repository.py` wird die Rechnungs-OP-Balance am Buchungsdatum der Gegenbuchung um `closed_open_amount` vermindert. Vor diesem Buchungsdatum bleibt die historische Forderung beziehungsweise Verbindlichkeit einschließlich der bis dahin gebuchten Zahlungen bestehen.

Stornobasierte Guthaben werden ab dem Buchungsdatum ihrer Guthabenumbuchung mit dem tatsächlich bebuchten Guthabenkonto und der passenden Rolle geführt. Die Umbuchung wird als bekannte OP-Bewegung markiert. Verrechnungsereignisse vermindern das Guthaben anschließend anhand des Buchungsdatums der Verrechnung. Die Hauptbuch- und Nebenbuchwerte wurden für Kundenforderungen, Lieferantenverbindlichkeiten, Kundenguthaben und Lieferantenguthaben miteinander abgeglichen.

## Geänderte Dateien

- `src/simpleob/database/open_item_overview_repository.py`
- `src/simpleob/database/open_item_reconciliation_repository.py`
- `tests/integration/test_open_item_overview.py`
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe4D3a_Etappe3B_Implementierung.md`

Die vorherigen, unabhängigen Arbeitsbaumänderungen wurden nicht bearbeitet. Es wurde keine Migration angelegt, keine PostgreSQL-Verbindung verwendet und kein Commit erstellt.

## Prüfungen

Ausgeführt:

```text
.venv/bin/python -m pytest -q \
  tests/integration/test_open_item_overview.py \
  tests/integration/test_open_item_reconciliation.py \
  tests/integration/test_open_item_payment.py \
  tests/integration/test_open_item_offset.py \
  tests/integration/test_payment_allocation_correction.py \
  -k 'not postgresql'
```

Ergebnis: **51 bestanden, 1 PostgreSQL-Test ausgelassen**.

Die Etappen-3B-Ergänzungen prüfen Kunden- und Lieferantenrechnungen mit mehreren Zahlungen und wirksamer Zuordnungskorrektur, das vollständig bezahlte Szenario, Stichtage vor und am Stornodatum, die spätere Teilverrechnung des Storno-Guthabens sowie passende Hauptbuch- und OP-Salden. Bestehende Tests sichern Gutschrift-Guthaben und 4D-2-Stornos weiter ab.

## Abgrenzung und offene Punkte

Die OP-Übersicht bleibt eine aktuelle Auswertung; sie wurde nicht zu einer historischen Stichtagsübersicht erweitert. Die Stichtagsberechnung betrifft weiterhin die vier Sammelkonto-Rollen. UI- oder Buchungsfunktionen wurden nicht ergänzt. Stornos von Rechnungen mit Gutschriftenverrechnungshistorie bleiben ausgeschlossen und sind Gegenstand des späteren Schritts 4D-3b. E-Bilanz/ERiC, Datenbankmigrationen und Mandantentransferfunktionen blieben unverändert.
