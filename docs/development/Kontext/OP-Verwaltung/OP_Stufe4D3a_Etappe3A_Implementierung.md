# SimpleOB – Stufe 4D-3a, Etappe 3A: Implementierungsbericht

## Umfang

Implementiert ist die atomare Stornierung teilweise oder vollständig bezahlter Kunden- und Lieferantenrechnungen ohne Gutschriftenverrechnungshistorie. Die vorhandene Rechnungsgegenbuchung bleibt ein dedizierter OP-Schreibweg; die allgemeine `BookingRepository.add()`-Sperre aus 4D-1 wurde nicht gelockert.

## Geänderte Dateien

- `src/simpleob/database/open_item_invoice_cancellation_repository.py`
- `src/simpleob/database/open_item_payment_repository.py`
- `src/simpleob/database/open_item_offset_repository.py`
- `src/simpleob/services/open_item_invoice_cancellation_service.py`
- `tests/integration/test_open_item_overview.py`
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe4D3a_Etappe3A_Implementierung.md`

Keine neue Migration, kein Datenmodellumbau und keine Änderungen an UI, OP-Übersicht oder Stichtagsabstimmung.

## Beträge und Hauptbuch

Die Stornotransaktion bewertet Zahlungsereignisse und Korrekturereignisse innerhalb der Transaktion neu. Die Bewertung muss mit dem bestehenden Rechnungs-OP-Rest übereinstimmen; Verrechnungshistorie, unbekannte Korrekturbuchungsdaten, unzulässige Datumsreihenfolge und inkonsistente Beträge führen zum Abbruch.

- `I` ist der unveränderte Rechnungsbetrag und zugleich `RechnungsOPStorno.amount`.
- `P` ist die wirksam bezahlte Summe aus Zahlungsereignissen und signierten Korrekturereignissen.
- `R = I − P` wird als `closed_open_amount` gespeichert.
- Es wird `0 <= P <= I` und `0 <= R <= I` verlangt.

Die vollständige Gegenbuchung spiegelt weiterhin jede Originalzeile mit vertauschter Soll-/Haben-Seite und verweist als `REVERSAL` auf die Originalbuchung. Vorhandene Zahlungsbuchungen bleiben unverändert.

Bei `P > 0` entsteht eine zweite, reine Hauptbuchumbuchung über exakt `P`:

- Kunde: tatsächlich bebuchtes Forderungskonto im Soll, konfigurierte Rolle `CUSTOMER_CREDIT_BALANCES` im Haben.
- Lieferant: konfigurierte Rolle `SUPPLIER_CREDIT_BALANCES` im Soll, tatsächlich bebuchtes Verbindlichkeitskonto im Haben.

Die Guthabenkontenrolle wird mandantenspezifisch über `ChartOfAccountsRepository` geladen und mit der bestehenden Aktiv-/Passivkontenvalidierung geprüft. Das Rechnungskonto wird aus der tatsächlichen Originalbuchung ermittelt. Es werden keine Kontonummern neu festgelegt. Bei `P = 0` entstehen weder Umbuchung noch Guthaben-OP.

Der Stornokopf speichert `amount = I`, `closed_open_amount = R`, die Rechnungsgegenbuchung und bei `P > 0` die Referenz `credit_booking_id`. Der neue Guthaben-OP erhält `amount = P`, `invoice_cancellation_id` als Herkunft und keine künstliche Gutschrift.

## Transaktion und Sperren

Alle Schreibvorgänge verwenden dieselbe SQLAlchemy-Session. Die Rechnungsgegenbuchung wird im dedizierten OP-Pfad gespeichert; die Guthabenumbuchung wird mit `BookingRepository.add(..., commit=False)` ergänzt. Danach werden Stornokopf und Guthaben-OP gespeichert. Es gibt keinen Zwischen-Commit; ein Fehler führt zum Rollback der Gegenbuchung, Umbuchung und Nebenbuchdaten.

Die Sperrreihenfolge folgt den vorhandenen Zahlungs-, Verrechnungs- und Korrekturpfaden: zunächst OP-Zeile, danach Geschäftsjahr. Das Geschäftsjahr wird vor dem Schreiben nochmals unter Sperre geprüft. Unter PostgreSQL sperrt die OP-Abfrage mit `FOR UPDATE`; auf SQLite gibt es keine entsprechende Zeilensperre. SQLite-Schreibkonflikte scheitern innerhalb der Transaktion und werden zurückgerollt; eine portable SQLite-Zeilensperre wird nicht behauptet.

## Guthabenverrechnung

`OpenItemOffsetRepository.get_credit()` und `list_open_credits()` lösen jetzt beide zulässigen Guthabenherkünfte auf. Bei einer Gutschrift bleibt der bisherige Pfad erhalten. Bei Rechnungsstorno werden Mandant, Partner und Richtung über den Stornokopf und die Ursprungsrechnung geprüft; das reale Gegenkonto wird aus der referenzierten Guthabenumbuchung gelesen. Die bestehenden Verrechnungsbuchungen und OP-Ereignisse werden wiederverwendet.

Der Integrationstest verrechnet einen Teil eines neu erzeugten Storno-Guthabens und prüft den verbleibenden Guthabenbetrag.

## Tests und Prüfungen

Ausgeführt:

```text
.venv/bin/python -m pytest -q \
  tests/integration/test_open_item_overview.py \
  tests/integration/test_open_item_payment.py \
  tests/integration/test_open_item_offset.py \
  tests/integration/test_payment_allocation_correction.py \
  -k 'not postgresql'
```

Ergebnis: **42 passed, 1 deselected**. Der PostgreSQL-spezifische Test wurde nicht ausgeführt und es wurde keine PostgreSQL-Verbindung hergestellt.

Ruff für die geänderten Python-Dateien und `git diff --check` bestanden.

Die Tests prüfen Kunden- und Lieferantenrechnung, Teilzahlung mit mehreren Zahlungen und Korrektur, Vollzahlung mit `R = 0`, exakte Spiegelung, Kontierungsrichtung und Betragsgleichheit, fehlende Guthabenkontenrolle, unveränderte Zahlungs-/Bankbuchungen, genau einen Guthaben-OP, anschließende Guthabenverrechnung, vollständigen Rollback bei Commitfehler, Ausschluss von Verrechnungshistorie sowie bestehende unbezahlte 4D-2-Stornos.

## Verbleibende Einschränkungen

- Die OP-Übersicht, Detailhistorie und Stichtagsabstimmung wurden gemäß Abgrenzung nicht angepasst. Insbesondere laden diese Auswertungen Storno-Guthaben noch nicht allgemein über `invoice_cancellation_id`; die Abstimmung berücksichtigt den vollen `amount` statt `closed_open_amount` und kennt die zusätzliche Guthabenumbuchung noch nicht. Sie sind bis zu einer späteren Anpassung für bezahlte Stornos nicht als fachlich vollständig anzusehen.
- Es wurde keine neue UI-Aktion oder Vorschau für bezahlte Stornos ergänzt. Die Implementierung ist über den vorhandenen Servicepfad nutzbar; die interaktive Bedienung bleibt späterer Arbeit vorbehalten.
- Rechnungen mit Gutschriftenverrechnungshistorie bleiben ausgeschlossen. Deren Gegenbuchungen und Rücknahmeereignisse gehören zu 4D-3b.
- Rückzahlungen, Auszahlung von Guthaben, andere Geschäftsjahre, E-Bilanz/ERiC und Mandantendatenverwaltung blieben unverändert.
