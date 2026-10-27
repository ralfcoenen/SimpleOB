# SimpleOB – Stufe 4D-3a, Etappe 2: Zahlungsberechnung und Storno-Schutzprüfungen

## Ergebnis

Diese Etappe ergänzt ausschließlich eine lesende Zahlungs-/Zulassungsprüfung für eine spätere bezahlte Rechnungsstornierung und Guards gegen neue OP-Bewegungen auf bereits stornierten Rechnungen. Sie erzeugt keine Stornierung und keine Guthabenübertragungsbuchung. Die bestehende 4D-2-Stornierung unbezahlter Rechnungen bleibt erhalten.

## Geänderte Dateien

- `src/simpleob/domain/open_item_invoice_cancellation.py`
- `src/simpleob/database/open_item_invoice_cancellation_repository.py`
- `src/simpleob/database/open_item_payment_repository.py`
- `src/simpleob/database/open_item_offset_repository.py`
- `src/simpleob/database/payment_allocation_correction_repository.py`
- `src/simpleob/services/open_item_invoice_cancellation_service.py`
- `src/simpleob/services/open_item_offset_service.py`
- `src/simpleob/services/payment_allocation_correction_service.py`
- `tests/integration/test_open_item_overview.py`

Keine Datenbankmigration war erforderlich.

## Zahlungsberechnung und Zulassungsprüfung

`OpenItemInvoiceCancellationService.assess_payment_history()` delegiert an das neue lesende `OpenItemInvoiceCancellationRepository.assess_payment_history()`. Das Ergebnis `InvoiceCancellationPaymentAssessment` enthält den OP-Ursprungsbetrag, Zahlungsereignissumme, signierte Korrekturdifferenz, wirksamen Zahlungsbetrag, Restbetrag und die maßgeblichen Buchungsdaten.

Die Berechnung lautet:

```text
P = Summe der Rechnungs-OP-Zahlungsereignisse
  + Summe der signierten Zahlungszuordnungskorrekturereignisse
R = Ursprungsbetrag − P
```

`SOURCE_RELEASE` wird als negatives Delta und `TARGET_APPLY` als positives Delta einbezogen. Für Sammelzahlungen zählt nur der jeweilige Rechnungs-OP-Anteil. Die Summe aller OP-Zahlungsereignisse einer Zahlung muss dem Zahlungsbetrag entsprechen. Mandant, Geschäftspartner, Zahlungsrichtung, Originalzuordnung, Korrekturkopf und Korrekturereignisse werden auf Konsistenz geprüft. `P < 0`, `P > Ursprungsbetrag`, widersprüchliche Ereignisse oder ein vom bestehenden `OpenItemPaymentRepository.get_open_invoice()` abweichender Restbetrag führen zum Abbruch.

Jede Verrechnungshistorie führt weiterhin zur Ablehnung. Der Assessment-Pfad erlaubt nur Zahlungs- und Korrekturhistorie; der bestehende 4D-2-Pfad verwendet weiterhin seine strengere Prüfung ohne Zahlungs-, Verrechnungs- oder Korrekturhistorie.

Für Zahlungen wird das Datum aus `Zahlung.booking_id → Buchung.booking_date` verwendet. Für alle Korrekturen, bei denen der OP Quelle oder Ziel ist, wird ausschließlich das gespeicherte `booking_date` berücksichtigt, auch ohne eigene Hauptbuchumbuchung. Ein NULL-Datum blockiert die Prüfung; es wird kein Ersatzdatum geschätzt. Das vorgeschlagene Stornobuchungsdatum muss mindestens dem spätesten Zahlungs- oder Korrekturbuchungsdatum entsprechen und im selben offenen Geschäftsjahr liegen.

## Schutz stornierter Rechnungs-OPs

`OpenItemPaymentRepository.ensure_not_cancelled()` stellt den gemeinsamen Storno-Guard bereit. Der Zahlungsrepository-Schreibpfad, der Verrechnungsservice und dessen Repository sowie Korrekturservice und Korrekturrepository prüfen stornierte OPs. Korrekturen werden sowohl für den Quell- als auch den Ziel-OP gesperrt. Der Guard ist nicht auf UI-Verhalten beschränkt.

## Tests

Ausgeführt wurden gezielte Tests aus:

- `tests/integration/test_open_item_overview.py` – neue Berechnungs-, Datums-, Historien- und Storno-Guard-Fälle sowie bestehende 4D-2-Stornofälle für Kunden und Lieferanten;
- `tests/integration/test_open_item_payment.py`;
- `tests/integration/test_payment_allocation_correction.py`.

Die abschließenden Absicherungen ergänzen einen Test mit zwei Teilkorrekturen derselben ursprünglichen Zahlungszuordnung. Er prüft die SOURCE_RELEASE-Summe von −25,00 €, die TARGET_APPLY-Summe von 25,00 €, den wirksamen Zahlungsbetrag von 25,00 € und den Restbetrag von 94,00 € auf Quell- und Zielrechnung. Zusätzlich sperrt das Korrektur-Repository jetzt Quell- und Ziel-OP in derselben Reihenfolge wie der Service, bevor es die ursprüngliche Zuordnung sperrt.

Im Abschlusslauf bestanden **28 fokussierte Tests**: 7 ausgewählte Assessment- und Storno-Guard-Tests sowie 21 Tests der Zahlungs-, Verrechnungs- und Korrektur-Regressionen. Ruff für die geänderten Python-Dateien und `git diff --check` bestanden ebenfalls. Es wurde keine PostgreSQL-Verbindung verwendet.

## Abgrenzung und verbleibende Arbeit

Noch nicht implementiert sind die Stornierung teilweise oder vollständig bezahlter Rechnungen, eine Guthabenübertragungsbuchung, ein Guthaben-OP aus Rechnungsstorno, die darauf angepasste OP-Restberechnung sowie Übersicht und Stichtagsabstimmung. Das Assessment ist keine Schreibautorisierung und wird derzeit nicht in der GUI angeboten. Diese Arbeiten gehören zu den folgenden Etappen. Gutschriftenverrechnungshistorie bleibt bis 4D-3b ausgeschlossen.
